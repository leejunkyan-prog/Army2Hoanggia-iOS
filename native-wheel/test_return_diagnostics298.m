#import <UIKit/UIKit.h>
#include <pthread.h>
#include <mach/mach.h>
#include <unistd.h>
#include <stdatomic.h>
#include <dlfcn.h>
#include <stdlib.h>
#include "ReturnDiagnostics.h"

static pthread_mutex_t waitLock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t waitCondition=PTHREAD_COND_INITIALIZER;
static atomic_int ready,released,resumed,stop;
static pthread_t stalledThread,healthyThread;
extern const char AGThreadTestReturnSite[];
__attribute__((noinline,optnone)) static void holdGameThread(void){
    pthread_mutex_lock(&waitLock);atomic_store(&ready,1);
    while(!atomic_load(&released)){
        pthread_cond_wait(&waitCondition,&waitLock);
        __asm__ volatile(".globl _AGThreadTestReturnSite\n_AGThreadTestReturnSite:");
    }
    pthread_mutex_unlock(&waitLock);
}
static void *stalled(void *unused){
    AGReturnPulse(0,0);holdGameThread();atomic_store(&resumed,1);
    while(!atomic_load(&stop)){AGReturnPulse(0,0);usleep(30000);}
    return NULL;
}
static void *healthy(void *unused){
    while(!atomic_load(&stop)){AGReturnPulse(1,0);usleep(30000);}
    return NULL;
}
static NSString *documents(void){return NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;}
static NSDictionary *readReport(void){
    NSData *data=[NSData dataWithContentsOfFile:[documents() stringByAppendingPathComponent:@"Watch298-diagnostic.json"]];
    return data?[NSJSONSerialization JSONObjectWithData:data options:0 error:nil]:nil;
}
static void finish(BOOL passed,NSString *reason){
    atomic_store(&stop,1);
    pthread_mutex_lock(&waitLock);atomic_store(&released,1);pthread_cond_signal(&waitCondition);pthread_mutex_unlock(&waitLock);
    pthread_join(stalledThread,NULL);pthread_join(healthyThread,NULL);
    NSDictionary *result=@{@"passed":@(passed),@"reason":reason};
    [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil]
        writeToFile:[documents() stringByAppendingPathComponent:@"diagnostics298-result.json"] atomically:YES];
    exit(passed?0:1);
}
@interface Diagnostic298App : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@property(nonatomic,strong) NSTimer *render;
@end
@implementation Diagnostic298App
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options{
    self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];
    self.window.rootViewController=[UIViewController new];[self.window makeKeyAndVisible];
    pthread_create(&stalledThread,NULL,stalled,NULL);pthread_create(&healthyThread,NULL,healthy,NULL);
    /* PB3 has no visible render/input callback: idle/background is expected. */
    AGReturnPulse(2,0);
    int fields[RD_COUNT]={0};fields[RD_OK]=1;fields[RD_SCREEN]=1;fields[RD_ROWS]=130;fields[RD_TRANSITION]=432;
    AGReturnPublish(0,fields);
    self.render=[NSTimer scheduledTimerWithTimeInterval:.1 repeats:YES block:^(NSTimer *timer){AGReturnPulse(0,1);}];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,3200*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
        @try{
            NSCAssert(atomic_load(&ready),@"Worker never entered the real native condition wait");
            /* Independent logger must capture the stall without Save driving it. */
            NSDictionary *report=readReport();NSArray *samples=report[@"thread_samples"];
            NSCAssert([report[@"build"] intValue]==298&&samples.count>0,@"Independent timer did not export a stalled thread");
            NSDictionary *event=samples.lastObject;
            NSCAssert([event[@"pb"] intValue]==1&&[event[@"game_age_ms"] intValue]>=1500,@"Wrong PB or fabricated liveness failure");
            NSDictionary *thread=event[@"game_thread"];
            NSCAssert([thread[@"state_status"] intValue]==KERN_SUCCESS&&[thread[@"run_state"] intValue]==TH_STATE_WAITING,@"Could not read the real waiting worker");
            Dl_info image={0};dladdr(AGThreadTestReturnSite,&image);
            uint64_t site=(uintptr_t)AGThreadTestReturnSite-(uintptr_t)image.dli_fbase;
            BOOL found=NO;
            for(NSDictionary *frame in thread[@"frames"]){
                NSCAssert(frame.count<=2&&frame[@"image"]!=nil,@"Stack memory or a raw address entered the export");
                if([frame[@"image"] isEqualToString:@"ReturnDiagnostics298"]){
                    uint64_t offset=strtoull([frame[@"offset"] UTF8String],NULL,16);
                    if(offset+64>=site&&offset<=site+64)found=YES;
                }
            }
            NSCAssert(found,@"Backtrace missed the actual caller of pthread_cond_wait");
            NSCAssert(![event[@"game_resumed_during_sample"] boolValue],@"Sampler resumed the worker");
            for(NSDictionary *e in samples)NSCAssert([e[@"pb"] intValue]==1,@"Healthy or invisible PB was reported as stuck");
            NSDictionary *pb2=report[@"latest"][1];
            NSCAssert([pb2[@"game_ticks"] intValue]>40&&[pb2[@"game_age_ms"] intValue]<500,@"Other PB heartbeat was interrupted");
            NSCAssert(self.window.isKeyWindow&&app.keyWindow==self.window,@"Sampler changed key window ownership");
            AGReturnDiagnosticSave();NSUInteger count=[readReport()[@"thread_samples"] count];
            AGReturnDiagnosticSave();NSCAssert([readReport()[@"thread_samples"] count]==count,@"Repeated saves flooded the trace ring");
            pthread_mutex_lock(&waitLock);atomic_store(&released,1);pthread_cond_signal(&waitCondition);pthread_mutex_unlock(&waitLock);
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,250*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
                @try{
                    AGReturnDiagnosticSave();NSDictionary *after=readReport();NSDictionary *pb=after[@"latest"][0];
                    NSCAssert(atomic_load(&resumed)&&[pb[@"game_ticks"] intValue]>2&&[pb[@"game_age_ms"] intValue]<200,@"Worker did not resume normally");
                    NSCAssert([after[@"thread_samples"] count]==count,@"Recovered worker generated another stall sample");
                    finish(YES,@"Real stopped pthread: waiting state and exact native wait caller exported automatically; other PB stays live; idle PB ignored; bounded samples; no thread suspension or window changes; normal recovery retained");
                }@catch(NSException *e){finish(NO,e.reason?:e.name);}
            });
        }@catch(NSException *e){finish(NO,e.reason?:e.name);}
    });
    return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(Diagnostic298App.class));}}
