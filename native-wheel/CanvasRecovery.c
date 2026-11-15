/* A dead Mach send right establishes that the old canvas thread cannot run
   again. Restart its original Runnable through java.lang.Thread.start only
   after spectator cleanup. Never step native UI/physics on a second clock. */
#include "CanvasRecovery.h"
#ifdef AG_CANVAS_RECOVERY
#include "ThreadDiagnostics.h"
#include "ReturnDiagnostics.h"
#include "SpectatorNative.h"
#include "Spectator.h"
#include "NotesMap.h"
#include "TurnMap.h"
#include <mach-o/dyld.h>
#include <stdatomic.h>
#include <time.h>
#include <string.h>
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static struct {
    atomic_uint_fast64_t attempts,recovered,failures;
    atomic_int armed,pending,status;
    atomic_bool busy,tracking;
    atomic_int trackAttempts;
    atomic_uintptr_t runnable;
    int wasWatching,cycleAttempts;
    uint64_t startedAt,retryAt,endedAt;
    void *thread;
} loops[6];
static uint64_t millis(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static uintptr_t base(void){return (uintptr_t)_dyld_get_image_header(0);}
#ifdef AG_CANVAS_RECOVERY_FIXTURE
extern uint8_t *AGRecoveryFixtureCanvas(int v),*AGRecoveryFixtureArena(int v);
static uint8_t *canvasClass(int v){return AGRecoveryFixtureCanvas(v);}
static uint8_t *arenaClass(int v){return AGRecoveryFixtureArena(v);}
#else
static uint8_t *canvasClass(int v){return *(uint8_t **)(base()+AGNotesMaps[v].canvas);}
static uint8_t *arenaClass(int v){return *(uint8_t **)(base()+AGTurnMaps[v].arena_class);}
#endif
static void localDelete(void *e,void *p){if(p)((void (*)(void *,void *))(*(void ***)e)[23])(e,p);}
static void globalDelete(void *e,void *p){if(p)((void (*)(void *,void *))(*(void ***)e)[22])(e,p);}
static int pendingException(void *e){
    void **jni=*(void ***)e;
    if(!((uint8_t (*)(void *))jni[228])(e))return 0;
    ((void (*)(void *))jni[17])(e);return 1;
}
typedef struct {int v,alive;void *clazz,*localThread,*thread;} ThreadJob;
typedef struct {int v;void *clazz,*current,*target,*root;} CaptureJob;
static int captureRunnable(void *e,void *opaque){
    CaptureJob *j=opaque;void **jni=*(void ***)e;
    j->clazz=((void *(*)(void *,const char *))jni[6])(e,"java/lang/Thread");
    if(pendingException(e)||!j->clazz)return 0;
    void *current=((void *(*)(void *,void *,const char *,const char *))jni[113])(e,j->clazz,"currentThread","()Ljava/lang/Thread;");
    if(pendingException(e)||!current)return 0;
    j->current=((void *(*)(void *,void *,void *,const void *))jni[116])(e,j->clazz,current,NULL);
    if(pendingException(e)||!j->current)return 0;
    void *field=((void *(*)(void *,void *,const char *,const char *))jni[94])(e,j->clazz,"target","Ljava/lang/Runnable;");
    if(pendingException(e)||!field)return 0;
    j->target=((void *(*)(void *,void *,void *))jni[95])(e,j->current,field);
    if(pendingException(e)||!j->target||*(void **)j->target!=canvasClass(j->v))return 0;
    j->root=((void *(*)(void *,void *))jni[21])(e,j->target);
    return !pendingException(e)&&j->root;
}
static int startThread(void *e,void *opaque){
    ThreadJob *j=opaque;void **jni=*(void ***)e;
    uint8_t *canvas=canvasClass(j->v);
    uint8_t *target=(void *)atomic_load(&loops[j->v].runnable);
    /* Retained on the original game thread, before it can exit. Static
       canvas screen/navigation fields must never substitute for Runnable. */
    if(!target||*(void **)target!=canvas)return -2;
    j->clazz=((void *(*)(void *,const char *))jni[6])(e,"java/lang/Thread");
    if(!j->clazz)return 0;
    if(pendingException(e))return 0;
    void *ctor=((void *(*)(void *,void *,const char *,const char *))jni[33])(e,j->clazz,"<init>","(Ljava/lang/Runnable;)V");
    if(pendingException(e)||!ctor)return 0;
    void *start=((void *(*)(void *,void *,const char *,const char *))jni[33])(e,j->clazz,"start","()V");
    if(pendingException(e)||!ctor||!start)return 0;
    /* jvalue is an eight-byte union on this exact ARM64 JNI ABI. */
    const void *argument[1]={target};
    j->localThread=((void *(*)(void *,void *,void *,const void *))jni[30])(e,j->clazz,ctor,argument);
    if(pendingException(e)||!j->localThread)return 0;
    j->thread=((void *(*)(void *,void *))jni[21])(e,j->localThread);
    if(pendingException(e)||!j->thread)return 0;
    ((void (*)(void *,void *,void *,const void *))jni[63])(e,j->thread,start,NULL);
    return pendingException(e)?0:1;
}
static int aliveThread(void *e,void *opaque){
    ThreadJob *j=opaque;void **jni=*(void ***)e;
    j->clazz=((void *(*)(void *,void *))jni[31])(e,j->thread);
    if(pendingException(e)||!j->clazz)return -1;
    void *method=((void *(*)(void *,void *,const char *,const char *))jni[33])(e,j->clazz,"isAlive","()Z");
    if(pendingException(e)||!method)return -1;
    int alive=((uint8_t (*)(void *,void *,void *,const void *))jni[39])(e,j->thread,method,NULL);
    if(pendingException(e))return -1;
    j->alive=alive!=0;return 1;
}
static int guard(void *e,int (*fn)(void *,void *),void *j){return AGWheelGuard(e,fn,j,(void *)(base()+0x1300d54));}
void AGCanvasRecoveryTrack(void *e,int v){
    if(!e||v<0||v>=6||atomic_load(&loops[v].runnable)||atomic_load(&loops[v].trackAttempts)>=3||atomic_exchange(&loops[v].tracking,1))return;
    atomic_fetch_add(&loops[v].trackAttempts,1);
    CaptureJob j={.v=v};int ok=guard(e,captureRunnable,&j);
    localDelete(e,j.target);localDelete(e,j.current);localDelete(e,j.clazz);pendingException(e);
    if(ok>0){uintptr_t empty=0;if(!atomic_compare_exchange_strong(&loops[v].runnable,&empty,(uintptr_t)j.root))globalDelete(e,j.root);}
    else{globalDelete(e,j.root);atomic_store(&loops[v].status,-10);}
    atomic_store(&loops[v].tracking,0);
}
static int safeDestination(int v){
    uint8_t *canvas=canvasClass(v);
    uint8_t *arena=arenaClass(v);
    void *screen=canvas?*(void **)(canvas+0xb8):NULL;
    /* A remaining arena means native cleanup has not completed. */
    return screen&&(!arena||screen!=*(void **)(arena+0xe8));
}
static void frame(void *e,int v,int watching){
    if(watching){
        if(!loops[v].wasWatching)loops[v].cycleAttempts=0;
        loops[v].wasWatching=1;atomic_store(&loops[v].armed,1);return;
    }
    if(loops[v].wasWatching)loops[v].endedAt=millis();
    loops[v].wasWatching=0;
    if(!atomic_load(&loops[v].armed)||AGViewerActive(v)||!safeDestination(v))return;
    uint64_t at=millis();AGReturnDiagnostic d={0};AGReturnDiagnosticCopy(v,&d);
    if(!atomic_load(&loops[v].pending)&&d.gameAt>loops[v].endedAt+500&&at<d.gameAt+500&&!AGThreadGameExited(v)){
        atomic_store(&loops[v].armed,0);return;
    }
    if(atomic_load(&loops[v].pending)){
        /* A replacement must actually reach the original update hook. */
        if(d.gameAt>loops[v].startedAt&&!AGThreadGameExited(v)){
            globalDelete(e,loops[v].thread);loops[v].thread=NULL;
            atomic_store(&loops[v].pending,0);atomic_store(&loops[v].armed,0);
            atomic_store(&loops[v].status,2);atomic_fetch_add(&loops[v].recovered,1);return;
        }
        if(at<loops[v].startedAt+2000)return;
        ThreadJob check={.v=v,.thread=loops[v].thread,.alive=-1};int ok=guard(e,aliveThread,&check);
        localDelete(e,check.clazz);pendingException(e);
        /* Missing progress from a live/unknown worker never permits a second. */
        if(ok<=0||check.alive!=0){atomic_store(&loops[v].status,ok>0?3:-3);return;}
        globalDelete(e,loops[v].thread);loops[v].thread=NULL;
        atomic_store(&loops[v].pending,0);atomic_fetch_add(&loops[v].failures,1);
        loops[v].retryAt=at+1000;atomic_store(&loops[v].status,-2);return;
    }
    if(!atomic_load(&loops[v].runnable)||!d.gameAt||at<d.gameAt+1500||at<loops[v].retryAt||loops[v].cycleAttempts>=3||!AGThreadGameExited(v))return;
    /* Empty room0 data is still being installed by the receive callback. */
    if(AGNativeWatchRoomStatus(e,v)==0)return;
    if(!AGThreadRebindGame(v))return;
    loops[v].cycleAttempts++;atomic_fetch_add(&loops[v].attempts,1);
    loops[v].startedAt=at;ThreadJob start={.v=v};int ok=guard(e,startThread,&start);
    localDelete(e,start.localThread);localDelete(e,start.clazz);pendingException(e);
    /* Retain even an uncertain start until isAlive proves it has ended. */
    if(start.thread){loops[v].thread=start.thread;atomic_store(&loops[v].pending,1);atomic_store(&loops[v].status,ok>0?1:-1);}
    else{
        globalDelete(e,start.thread);loops[v].retryAt=at+1000;
        atomic_fetch_add(&loops[v].failures,1);atomic_store(&loops[v].status,-1);
    }
}
void AGCanvasRecoveryFrame(void *e,int v,int watching){
    if(!e||v<0||v>=6||atomic_exchange(&loops[v].busy,1))return;
    frame(e,v,watching);atomic_store(&loops[v].busy,0);
}
int AGCanvasRecoveryCopy(int v,AGCanvasRecovery *out){
    if(v<0||v>=6||!out)return 0;
    *out=(AGCanvasRecovery){atomic_load(&loops[v].attempts),atomic_load(&loops[v].recovered),atomic_load(&loops[v].failures),
        atomic_load(&loops[v].armed),atomic_load(&loops[v].pending),atomic_load(&loops[v].status),atomic_load(&loops[v].runnable)!=0};return 1;
}
#endif
