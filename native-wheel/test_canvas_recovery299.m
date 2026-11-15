/* The production recovery scheduler runs unchanged. Only native game globals
   and the Java VM's Thread.start boundary are fixtures. Worker lifetime and
   Mach right death/rebinding use real pthreads and kernel calls. */
#import <UIKit/UIKit.h>
#include <mach/mach.h>
#include <pthread.h>
#include <stdatomic.h>
#include <unistd.h>
#include <string.h>
#include "ReturnDiagnostics.h"
#include "CanvasRecovery.h"
#include "ThreadDiagnostics.h"
static uint8_t canvases[6][0x200],arenas[6][0x300],targets[6][0x80],screens[6][0x80];
static uint8_t battleScreen[0x80];
uint8_t *AGRecoveryFixtureCanvas(int v){return canvases[v];}
uint8_t *AGRecoveryFixtureArena(int v){return arenas[v];}
static void pointer(void *p,void *value){memcpy(p,&value,sizeof value);}
static void *readPointer(void *p){void *value;memcpy(&value,p,sizeof value);return value;}
static void *jni[240],*env[1]={jni};
static atomic_int ready,leaveOld,stop,uiUpdates;
static int modal,rows=130,starts,globals,locals,peakGlobals;
static pthread_t oldWorker,healthyWorker,replacement,renderThread;
static pthread_mutex_t conditionLock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t condition=PTHREAD_COND_INITIALIZER;
typedef struct {int running;void *target;} JavaThread;
static JavaThread created;
static void *replacementMain(void *opaque){
    /* Delay the first canvas callback to expose repeated-render start races. */
    usleep(400000);
    while(!atomic_load(&stop)){AGReturnPulse(0,0);atomic_fetch_add(&uiUpdates,1);usleep(30000);}
    created.running=0;return NULL;
}
static void *oldMain(void *unused){
    AGCanvasRecoveryTrack(env,0);
    AGReturnPulse(0,0);
    pthread_mutex_lock(&conditionLock);atomic_store(&ready,1);
    while(!atomic_load(&leaveOld))pthread_cond_wait(&condition,&conditionLock);
    pthread_mutex_unlock(&conditionLock);return NULL;
}
static void *healthyMain(void *unused){
    while(!atomic_load(&stop)){AGReturnPulse(1,0);usleep(30000);}return NULL;
}
int AGViewerActive(int v){return modal;}
int AGNativeWatchRoomStatus(void *e,int v){return rows;}
int AGWheelGuard(void *e,int (*callback)(void *,void *),void *job,void *unused){return callback(e,job);}
static void *findClass(void *e,const char *name){
    NSCAssert(!strcmp(name,"java/lang/Thread"),@"Unexpected JNI class");locals++;return &jni;
}
static void *getMethod(void *e,void *c,const char *name,const char *signature){
    NSCAssert(pthread_equal(renderThread,pthread_self()),@"Native Java calls escaped the attached render callback");
    if(!strcmp(name,"<init>")){NSCAssert(!strcmp(signature,"(Ljava/lang/Runnable;)V"),@"Wrong Runnable constructor");return (void *)1;}
    if(!strcmp(name,"start")){NSCAssert(!strcmp(signature,"()V"),@"Wrong start signature");return (void *)2;}
    NSCAssert(!strcmp(name,"isAlive")&&!strcmp(signature,"()Z"),@"Unexpected Thread method");return (void *)3;
}
static void *newObject(void *e,void *c,void *method,const void **arguments){
    NSCAssert(method==(void *)1&&arguments[0]==targets[0],@"Replacement lost the original GameCanvas Runnable");
    created.target=(void *)arguments[0];locals++;return &created;
}
static void *newGlobal(void *e,void *p){globals++;if(globals>peakGlobals)peakGlobals=globals;return p;}
static void *staticMethod(void *e,void *c,const char *name,const char *signature){NSCAssert(!strcmp(name,"currentThread")&&!strcmp(signature,"()Ljava/lang/Thread;"),@"Wrong currentThread signature");return (void *)4;}
static void *currentThread(void *e,void *c,void *method,const void *arguments){locals++;return &oldWorker;}
static void *targetField(void *e,void *c,const char *name,const char *signature){NSCAssert(!strcmp(name,"target")&&!strcmp(signature,"Ljava/lang/Runnable;"),@"Wrong original Runnable field");return (void *)5;}
static void *originalTarget(void *e,void *thread,void *field){NSCAssert(field==(void *)5&&thread==&oldWorker,@"Target was not read on the original worker");locals++;return targets[0];}
static void deleteGlobal(void *e,void *p){globals--;}
static void deleteLocal(void *e,void *p){locals--;}
static int exceptionCheck(void *e){return 0;}
static void exceptionClear(void *e){}
static void start(void *e,JavaThread *thread,void *method,const void *arguments){
    NSCAssert(method==(void *)2&&!arguments&&thread==&created,@"Wrong JNI start call");
    starts++;NSCAssert(starts==1,@"A second canvas thread was created");
    /* Re-entry on Thread.start must not acquire a second recovery claim. */
    AGCanvasRecoveryFrame(env,0,0);
    thread->running=1;pthread_create(&replacement,NULL,replacementMain,thread);
}
static void *getClass(void *e,void *thread){locals++;return &jni;}
static int isAlive(void *e,JavaThread *thread,void *method,const void *arguments){return thread->running;}
static AGCanvasRecovery state(void){AGCanvasRecovery s={0};AGCanvasRecoveryCopy(0,&s);return s;}
static int kernelExit(void){
    /* pthread_join can complete just before the kernel tears down the Mach
       thread. Production waits for later render callbacks; allow that same
       teardown interval instead of assuming join implies a dead port. */
    for(int i=0;i<300&&!AGThreadGameExited(0);i++)usleep(1000);
    return AGThreadGameExited(0);
}
static NSString *documents(void){return NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;}
static void finish(BOOL passed,NSString *reason){
    atomic_store(&stop,1);
    pthread_mutex_lock(&conditionLock);atomic_store(&leaveOld,1);pthread_cond_signal(&condition);pthread_mutex_unlock(&conditionLock);
    if(starts)pthread_join(replacement,NULL);
    pthread_join(healthyWorker,NULL);
    NSDictionary *result=@{@"passed":@(passed),@"reason":reason,@"starts":@(starts),@"ui_updates":@(atomic_load(&uiUpdates)),@"global_roots":@(globals)};
    [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil]
        writeToFile:[documents() stringByAppendingPathComponent:@"recovery299-result.json"] atomically:YES];
    exit(passed?0:1);
}
@interface Recovery299App : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@end
@implementation Recovery299App
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options{
    self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];self.window.rootViewController=[UIViewController new];[self.window makeKeyAndVisible];
    renderThread=pthread_self();
    for(int v=0;v<6;v++){pointer(targets[v],canvases[v]);pointer(canvases[v]+0xb0,screens[v]);pointer(canvases[v]+0xb8,screens[v]);pointer(arenas[v]+0xe8,battleScreen);}
    jni[6]=findClass;jni[33]=getMethod;jni[30]=newObject;jni[21]=newGlobal;jni[22]=deleteGlobal;jni[23]=deleteLocal;
    jni[63]=start;jni[228]=exceptionCheck;jni[17]=exceptionClear;jni[31]=getClass;jni[39]=isAlive;
    jni[113]=staticMethod;jni[116]=currentThread;jni[94]=targetField;jni[95]=originalTarget;
    pthread_create(&oldWorker,NULL,oldMain,NULL);pthread_create(&healthyWorker,NULL,healthyMain,NULL);
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,1800*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
        @try{
            NSCAssert(atomic_load(&ready)&&state().registered&&!AGThreadGameExited(0),@"Original Runnable was not retained or real waiting worker was mistaken for a dead one");
            AGCanvasRecoveryFrame(env,0,1);AGCanvasRecoveryFrame(env,0,0);
            NSCAssert(starts==0&&state().attempts==0,@"Stale but live canvas acquired a second update owner");
            AGCanvasRecoveryFrame(env,0,1);
            pthread_mutex_lock(&conditionLock);atomic_store(&leaveOld,1);pthread_cond_signal(&condition);pthread_mutex_unlock(&conditionLock);
            pthread_join(oldWorker,NULL);
            NSCAssert(kernelExit(),@"Exited pthread did not produce a dead retained Mach right");
            AGCanvasRecoveryFrame(env,0,1);NSCAssert(starts==0,@"Canvas restarted inside an active watch");
            pointer(canvases[0]+0xb8,battleScreen);AGCanvasRecoveryFrame(env,0,0);NSCAssert(starts==0,@"Canvas restarted before native arena cleanup");
            pointer(canvases[0]+0xb8,screens[0]);rows=0;AGCanvasRecoveryFrame(env,0,0);NSCAssert(starts==0,@"Canvas restarted before area rows were installed");
            rows=130;modal=1;AGCanvasRecoveryFrame(env,0,0);NSCAssert(starts==0,@"Canvas restarted under a new watch offer");modal=0;
            AGCanvasRecoveryFrame(env,0,0);NSCAssert(starts==1&&state().pending,@"Dead canvas was not restarted through Thread.start");
            for(int i=0;i<120;i++)AGCanvasRecoveryFrame(env,0,0);
            NSCAssert(starts==1&&peakGlobals==2,@"Repeated renders duplicated a starting worker");
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,900*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
                @try{
                    AGCanvasRecoveryFrame(env,0,0);
                    AGCanvasRecovery s=state();AGReturnDiagnostic d={0},other={0};AGReturnDiagnosticCopy(0,&d);AGReturnDiagnosticCopy(1,&other);
                    NSCAssert(s.recovered==1&&!s.pending&&!s.armed&&s.status==2,@"Replacement never reached the original update heartbeat");
                    NSCAssert(!AGThreadGameExited(0)&&d.gameTicks>5&&atomic_load(&uiUpdates)>5,@"Rebinding did not retain the actual new worker");
                    NSCAssert(other.gameTicks>30,@"Other PB stopped updating");
                    NSCAssert(globals==1&&locals==0,@"Expected one retained original Runnable and no temporary thread roots");
                    NSCAssert(self.window.isKeyWindow&&app.keyWindow==self.window,@"Recovery changed key window ownership");
                    AGReturnDiagnosticSave();
                    NSData *data=[NSData dataWithContentsOfFile:[documents() stringByAppendingPathComponent:@"Watch299-diagnostic.json"]];
                    NSDictionary *report=[NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
                    NSCAssert([report[@"latest"][0][@"canvas_recovery"][@"recovered"] intValue]==1,@"Recovery evidence was not exported");
                    for(int i=0;i<100;i++)AGCanvasRecoveryFrame(env,0,0);
                    NSCAssert(starts==1,@"Healthy resumed canvas was restarted again");
                    finish(YES,@"Actual waiting worker is preserved; actual exited pthread is detected; active watch/arena/empty rows/offer defer restart; exactly one original Runnable starts despite re-entry and delayed heartbeat; real Mach port rebind, independent PB updates, normal UI counter progress, JNI roots and key window retained");
                }@catch(NSException *e){finish(NO,e.reason?:e.name);}
            });
        }@catch(NSException *e){finish(NO,e.reason?:e.name);}
    });
    return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(Recovery299App.class));}}
