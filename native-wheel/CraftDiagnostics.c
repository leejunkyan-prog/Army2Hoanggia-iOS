/* Scalars only. Never modify inventory rows, selection, JNI handles, input,
   packet positions or requests. The file worker receives copied values. */
#include "CraftDiagnostics.h"
#ifdef AG_CRAFT_DIAGNOSTIC
#include <pthread.h>
#include <string.h>
#include <time.h>
#include <mach-o/dyld.h>
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static pthread_mutex_t craftLock=PTHREAD_MUTEX_INITIALIZER;
static AGCraftDiagnostic diagnostics[6];
static uint64_t lastDetail[6];
static AGCraftEvent events[AG_CRAFT_EVENTS];
static unsigned nextEvent,eventCount;
static uint64_t millis(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static void record(AGCraftEvent event){
    pthread_mutex_lock(&craftLock);
    events[nextEvent]=event;nextEvent=(nextEvent+1)%AG_CRAFT_EVENTS;
    if(eventCount<AG_CRAFT_EVENTS)eventCount++;
    pthread_mutex_unlock(&craftLock);
}
void AGCraftPublish(int v,const int64_t fields[CF_COUNT]){
    if(v<0||v>=6||!fields)return;
    uint64_t at=millis();pthread_mutex_lock(&craftLock);
    memcpy(diagnostics[v].values,fields,sizeof diagnostics[v].values);diagnostics[v].at=at;
    pthread_mutex_unlock(&craftLock);
}
typedef struct {int v;void *item;int64_t values[CF_COUNT];} Sample;
static int inspect(void *e,void *opaque){Sample *s=opaque;return AGInventoryCraftInspect(s->v,s->item,s->values);}
static int guarded(void *e,Sample *s){return AGWheelGuard(e,inspect,s,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));}
void AGCraftSample(void *e,int v){
    if(!e||v<0||v>=6)return;
    Sample s={.v=v};int ok=guarded(e,&s);if(ok<0)s.values[CF_OK]=-1;AGCraftPublish(v,s.values);
}
static void itemValues(void *opaque,int64_t *kind,int64_t *id,int64_t *quantity){
    uint8_t *p=opaque;*kind=0;*id=-1;*quantity=-1;if(!p)return;
    *kind=p[0xbd]?2:1;
    /* Only public consumable/template IDs. Equipment's server UID is omitted. */
    if(p[0xbd]){*id=*(int64_t *)(p+0x80);*quantity=*(int64_t *)(p+0x90);}
}
void AGCraftDetail(void *e,void *original,void *resolved,int result,int reason){
    if(!e)return;
    AGCraftEvent event={.at=millis()};int64_t *d=event.values;
    d[CE_KIND]=1;d[CE_PB]=-1;d[CE_RESULT]=result;d[CE_REASON]=reason;
    itemValues(original,&d[CE_INPUT_KIND],&d[CE_INPUT_ID],&d[CE_INPUT_QUANTITY]);
    itemValues(resolved,&d[CE_OUTPUT_KIND],&d[CE_OUTPUT_ID],&d[CE_OUTPUT_QUANTITY]);
    d[CE_HANDLE_CHANGED]=original!=resolved;
    for(int v=0;v<6;v++){
        Sample before={.v=v,.item=original};int ok=guarded(e,&before);
        Sample after={.v=v,.item=resolved};int afterOK=guarded(e,&after);
        if(ok<=0||afterOK<=0||!before.values[CF_SCREEN]||
           !(before.values[CF_OPAQUE_IS_SLOT]||before.values[CF_OPAQUE_IS_CACHE]||before.values[CF_OPAQUE_IN_SOURCE]||
             after.values[CF_OPAQUE_IS_SLOT]||after.values[CF_OPAQUE_IS_CACHE]||after.values[CF_OPAQUE_IN_SOURCE]))continue;
        AGCraftPublish(v,after.values);
        d[CE_PB]=v+1;d[CE_INPUT_SELECTED]=before.values[CF_OPAQUE_IS_SLOT]||before.values[CF_OPAQUE_IS_CACHE];
        d[CE_OUTPUT_IN_SOURCE]=after.values[CF_OPAQUE_IN_SOURCE];d[CE_SELECTED]=after.values[CF_SELECTED];
        pthread_mutex_lock(&craftLock);diagnostics[v].detailCalls++;
        if(result>0)diagnostics[v].accepted++;else diagnostics[v].rejected++;
        lastDetail[v]=event.at;pthread_mutex_unlock(&craftLock);break;
    }
    record(event);
}
void AGCraftReceive(void *message,int v){
    if(!message||v<0||v>=6)return;
    uint64_t at=millis();pthread_mutex_lock(&craftLock);
    int active=diagnostics[v].values[CF_SCREEN]!=0||(lastDetail[v]&&at>=lastDetail[v]&&at-lastDetail[v]<30000);
    if(active)diagnostics[v].packets++;
    pthread_mutex_unlock(&craftLock);if(!active)return;
    const uint8_t *m=message,*input=*(const uint8_t **)(m+0x20);
    int remaining=-1;
    if(input){const uint8_t *array=*(const uint8_t **)(input+0x10);
        if(array){int cap=*(const int *)(array+0x10),count=*(const int *)(input+0x18),pos=*(const int *)(input+0x20);
            if(pos>=0&&count>=pos&&count<=cap&&count-pos<=65535)remaining=count-pos;}}
    AGCraftEvent event={.at=at};event.values[CE_KIND]=2;event.values[CE_PB]=v+1;
    event.values[CE_COMMAND]=*(const int8_t *)(m+0x30);event.values[CE_LENGTH]=remaining;record(event);
}
void AGCraftRecipeBinding(int v,int status,int before,int after){
    AGCraftEvent event={.at=millis()};event.values[CE_KIND]=3;event.values[CE_PB]=v+1;
    event.values[CE_COMMAND]=-18;event.values[CE_BIND_BEFORE]=before;
    event.values[CE_BIND_AFTER]=after;event.values[CE_BIND_STATUS]=status;record(event);
}
int AGCraftDiagnosticCopy(int v,AGCraftDiagnostic *out){
    if(v<0||v>=6||!out)return 0;pthread_mutex_lock(&craftLock);*out=diagnostics[v];pthread_mutex_unlock(&craftLock);return 1;
}
int AGCraftEventsCopy(AGCraftEvent *out,int capacity){
    if(!out||capacity<1)return 0;pthread_mutex_lock(&craftLock);
    unsigned n=eventCount<(unsigned)capacity?eventCount:(unsigned)capacity;
    unsigned first=(nextEvent+AG_CRAFT_EVENTS-n)%AG_CRAFT_EVENTS;
    for(unsigned i=0;i<n;i++)out[i]=events[(first+i)%AG_CRAFT_EVENTS];
    pthread_mutex_unlock(&craftLock);return (int)n;
}
#endif
