/* Metadata only: no credentials, chat text or packet bodies are recorded. */
#include "WatchTrace.h"
#include "Spectator.h"
#include <stdatomic.h>
#include <pthread.h>
#include <string.h>
#include <stdio.h>
#include <mach-o/dyld.h>
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static struct {
    atomic_uint_fast64_t frames,packets,exceptions,waits,expirations;
    atomic_int command,operation,waitKind,waitActor,waitStage;
    char exception[512];
} traces[6];
static pthread_mutex_t traceLock=PTHREAD_MUTEX_INITIALIZER;
void AGNativeWatchTraceReset(int v){
    if(v<0||v>=6)return;
    atomic_store(&traces[v].frames,0);atomic_store(&traces[v].packets,0);
    atomic_store(&traces[v].exceptions,0);atomic_store(&traces[v].waits,0);
    atomic_store(&traces[v].expirations,0);atomic_store(&traces[v].command,0);
    atomic_store(&traces[v].operation,-1);atomic_store(&traces[v].waitKind,-1);
    atomic_store(&traces[v].waitActor,-1);atomic_store(&traces[v].waitStage,0);
    pthread_mutex_lock(&traceLock);traces[v].exception[0]=0;pthread_mutex_unlock(&traceLock);
}
void AGNativeWatchTraceFrame(int v){
    if(v>=0&&v<6&&AGViewerStillWatching(v))atomic_fetch_add(&traces[v].frames,1);
}
void AGNativeWatchTracePacket(int v,int cmd,int op){
    if(v<0||v>=6)return;
    atomic_fetch_add(&traces[v].packets,1);atomic_store(&traces[v].command,cmd);
    atomic_store(&traces[v].operation,op);
}
void AGNativeWatchTraceWait(int v,int kind,int actor,int stage){
    if(v<0||v>=6)return;
    atomic_store(&traces[v].waitKind,kind);atomic_store(&traces[v].waitActor,actor);
    atomic_store(&traces[v].waitStage,stage);
    if(stage==1)atomic_fetch_add(&traces[v].waits,1);
    if(stage==3)atomic_fetch_add(&traces[v].expirations,1);
}
typedef struct {void *exception;char text[512];} ExceptionText;
static int exceptionText(void *e,void *opaque){
    ExceptionText *j=opaque;void **jni=*(void ***)e;
    void *cls=((void *(*)(void *,void *))jni[31])(e,j->exception);
    if(!cls)return 0;
    void *method=((void *(*)(void *,void *,const char *,const char *))jni[33])(e,cls,"toString","()Ljava/lang/String;");
    if(!method){((void (*)(void *,void *))jni[23])(e,cls);return 0;}
    void *volatile string=((void *(*)(void *,void *,void *,const void *))jni[36])(e,j->exception,method,NULL);
    if(string){
        const char *utf=((const char *(*)(void *,void *,void *))jni[169])(e,string,NULL);
        if(utf){snprintf(j->text,sizeof j->text,"%s",utf);((void (*)(void *,void *,const char *))jni[170])(e,string,utf);}
        ((void (*)(void *,void *))jni[23])(e,string);
    }
    ((void (*)(void *,void *))jni[23])(e,cls);
    return j->text[0]!=0;
}
void AGNativeWatchTraceException(void *e,void *exception,int v){
    if(!e||!exception||v<0||v>=6||!AGViewerStillWatching(v))return;
    uint64_t count=atomic_fetch_add(&traces[v].exceptions,1);
    if(count)return; /* Retain the first actual failure; do not log every frame. */
    ExceptionText j={.exception=exception};
    int ok=AGWheelGuard(e,exceptionText,&j,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));
    pthread_mutex_lock(&traceLock);
    snprintf(traces[v].exception,sizeof traces[v].exception,"%s",ok>0?j.text:"Native battle update threw a Java exception");
    pthread_mutex_unlock(&traceLock);
}
int AGNativeWatchTraceCopy(int v,AGWatchTrace *out){
    if(v<0||v>=6||!out)return 0;
    *out=(AGWatchTrace){.frames=atomic_load(&traces[v].frames),.packets=atomic_load(&traces[v].packets),
        .exceptions=atomic_load(&traces[v].exceptions),.waits=atomic_load(&traces[v].waits),
        .expirations=atomic_load(&traces[v].expirations),.command=atomic_load(&traces[v].command),
        .operation=atomic_load(&traces[v].operation),.waitKind=atomic_load(&traces[v].waitKind),
        .waitActor=atomic_load(&traces[v].waitActor),.waitStage=atomic_load(&traces[v].waitStage)};
    pthread_mutex_lock(&traceLock);memcpy(out->exception,traces[v].exception,sizeof out->exception);pthread_mutex_unlock(&traceLock);
    return 1;
}
