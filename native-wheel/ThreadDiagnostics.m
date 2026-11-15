/* Sample only this process. No thread is suspended, signalled, resumed or
   unwound with Java/JNI. Only image-relative code locations enter the log. */
#import <Foundation/Foundation.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/thread_info.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <pthread.h>
#include <stdatomic.h>
#include <time.h>
#include "ThreadDiagnostics.h"
#include "ReturnDiagnostics.h"
#ifdef AG_RETURN_THREAD_DIAGNOSTIC
static atomic_uint gamePorts[6],renderPorts[6];
void AGThreadPulse(int v,int source){
    if(v<0||v>=6)return;
    atomic_uint *slot=source?&renderPorts[v]:&gamePorts[v];
    if(atomic_load(slot))return;
    /* Retain one send right per callback source, even if the thread exits. */
    mach_port_t port=mach_thread_self();unsigned empty=0;
    if(!atomic_compare_exchange_strong(slot,&empty,port))mach_port_deallocate(mach_task_self(),port);
}
static uint64_t nowMillis(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static uint64_t clean(uint64_t p){return p&UINT64_C(0x0000ffffffffffff);}
static NSDictionary *location(uint64_t pointer){
    uint64_t p=clean(pointer);uint32_t count=_dyld_image_count();
    for(uint32_t i=0;i<count;i++){
        const struct mach_header_64 *header=(const void *)_dyld_get_image_header(i);
        if(!header||header->magic!=MH_MAGIC_64)continue;
        intptr_t slide=_dyld_get_image_vmaddr_slide(i);
        const uint8_t *cursor=(const uint8_t *)(header+1),*end=cursor+header->sizeofcmds;
        for(uint32_t j=0;j<header->ncmds&&cursor+sizeof(struct load_command)<=end;j++){
            const struct load_command *command=(const void *)cursor;
            if(command->cmdsize<sizeof *command||cursor+command->cmdsize>end)break;
            if(command->cmd==LC_SEGMENT_64&&command->cmdsize>=sizeof(struct segment_command_64)){
                const struct segment_command_64 *segment=(const void *)cursor;
                uint64_t start=segment->vmaddr+slide;
                if((segment->initprot&VM_PROT_EXECUTE)&&p>=start&&p-start<segment->vmsize){
                    NSString *name=[NSString stringWithUTF8String:_dyld_get_image_name(i)?:"unknown"];
                    return @{ @"image":name.lastPathComponent?:@"unknown",
                        @"offset":[NSString stringWithFormat:@"0x%llx",(unsigned long long)(p-(uintptr_t)header)] };
                }
            }
            cursor+=command->cmdsize;
        }
    }
    return @{ @"image":@"unmapped" };
}
static NSDictionary *sampleThread(mach_port_t port){
    NSMutableDictionary *result=[NSMutableDictionary dictionary];
    thread_basic_info_data_t basic={0};mach_msg_type_number_t n=THREAD_BASIC_INFO_COUNT;
    kern_return_t info=thread_info(port,THREAD_BASIC_INFO,(thread_info_t)&basic,&n);
    result[@"info_status"]=@(info);
    if(info==KERN_SUCCESS){
        result[@"run_state"]=@(basic.run_state);result[@"suspend_count"]=@(basic.suspend_count);
        result[@"user_cpu_ms"]=@((int64_t)basic.user_time.seconds*1000+basic.user_time.microseconds/1000);
        result[@"system_cpu_ms"]=@((int64_t)basic.system_time.seconds*1000+basic.system_time.microseconds/1000);
    }
#if defined(__arm64__)
    arm_thread_state64_t state={0};n=ARM_THREAD_STATE64_COUNT;
    kern_return_t status=thread_get_state(port,ARM_THREAD_STATE64,(thread_state_t)&state,&n);
    result[@"state_status"]=@(status);
    if(status==KERN_SUCCESS){
        NSMutableArray *frames=[NSMutableArray array];
        [frames addObject:location(arm_thread_state64_get_pc(state))];
        [frames addObject:location(arm_thread_state64_get_lr(state))];
        uint64_t frame=clean(arm_thread_state64_get_fp(state));
        for(int i=0;i<46&&frame&&(frame&15)==0;i++){
            uint64_t pair[2]={0};mach_vm_size_t copied=0;
            kern_return_t read=mach_vm_read_overwrite(mach_task_self(),frame,sizeof pair,(mach_vm_address_t)pair,&copied);
            if(read!=KERN_SUCCESS||copied!=sizeof pair)break;
            [frames addObject:location(pair[1])];
            uint64_t next=clean(pair[0]);
            if(next<=frame||next-frame>1024*1024)break;
            frame=next;
        }
        result[@"frames"]=frames;
    }
#else
    result[@"state_status"]=@(-1);
#endif
    return result;
}
NSArray *AGThreadDiagnosticsSample(void){
    static NSMutableArray *history;static uint64_t sampledAt[6],sampledTick[6];
    if(!history)history=[NSMutableArray array];
    uint64_t at=nowMillis();
    for(int v=0;v<6;v++){
        AGReturnDiagnostic before={0};AGReturnDiagnosticCopy(v,&before);
        if(!before.gameAt||at<before.gameAt+1500)continue;
        /* A backgrounded application is expected to stop updating. Require
           a recent render or input callback for a real liveness failure. */
        uint64_t visible=before.renderAt>before.inputAt?before.renderAt:before.inputAt;
        if(!visible||at>visible+1200)continue;
        if(sampledTick[v]==before.gameTicks&&at<sampledAt[v]+5000)continue;
        sampledAt[v]=at;sampledTick[v]=before.gameTicks;
        NSMutableDictionary *event=[@{@"pb":@(v+1),@"uptime_ms":@(at),
            @"game_ticks":@(before.gameTicks),@"game_age_ms":@(at-before.gameAt),
            @"screen_kind":@(before.native[RD_SCREEN]),@"canvas_sequence":@(before.native[RD_CANVAS_STEP])} mutableCopy];
        mach_port_t target=atomic_load(&gamePorts[v]);
        event[@"game_thread"]=target?sampleThread(target):@{@"registration_missing":@YES};
        /* Capture native peers as well: a blocked Java monitor often needs
           both its waiter and its owning receive/render thread to explain it. */
        thread_act_array_t threads=NULL;mach_msg_type_number_t count=0;
        kern_return_t listed=task_threads(mach_task_self(),&threads,&count);
        event[@"threads_status"]=@(listed);NSMutableArray *peers=[NSMutableArray array];
        if(listed==KERN_SUCCESS){
            for(mach_msg_type_number_t i=0;i<count;i++){
                if(i<128&&threads[i]!=target){
                    NSMutableDictionary *peer=[sampleThread(threads[i]) mutableCopy];
                    BOOL relevant=NO;
                    for(NSDictionary *frame in peer[@"frames"]){
                        NSString *name=frame[@"image"];
                        if([name isEqualToString:@"Army2Hoanggia"]||[name isEqualToString:@"AGWheel"])relevant=YES;
                    }
                    NSMutableArray *roles=[NSMutableArray array];
                    for(int p=0;p<6;p++){
                        if(threads[i]==atomic_load(&gamePorts[p]))[roles addObject:[NSString stringWithFormat:@"game_pb%d",p+1]];
                        if(threads[i]==atomic_load(&renderPorts[p]))[roles addObject:[NSString stringWithFormat:@"render_pb%d",p+1]];
                    }
                    if(relevant||roles.count){peer[@"roles"]=roles;[peers addObject:peer];}
                }
                mach_port_deallocate(mach_task_self(),threads[i]);
            }
            vm_deallocate(mach_task_self(),(vm_address_t)threads,count*sizeof(thread_t));
        }
        event[@"related_threads"]=peers;
        AGReturnDiagnostic after={0};AGReturnDiagnosticCopy(v,&after);
        event[@"game_resumed_during_sample"]=@(after.gameTicks!=before.gameTicks);
        [history addObject:event];while(history.count>16)[history removeObjectAtIndex:0];
    }
    return [history copy];
}
#endif
