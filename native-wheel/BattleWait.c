#include <stdint.h>
#include <time.h>
#include <mach-o/dyld.h>
#include "NativeMap.h"
#include "NotesMap.h"
#include "TurnMap.h"
#include "ShipTrace.h"
#include "Spectator.h"
#include "SpectatorNative.h"
#include "WatchTrace.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
extern void AGTurnAwait(void *,void *,int,int,int);
typedef struct {
    int variant,room,local,airship;
    uintptr_t connection;
    uint8_t *arena,*canvas,*players,*projectiles;
} BattleWaitContext;
static uintptr_t imageBase(void){return (uintptr_t)_dyld_get_image_header(0);}
static int readContext(void *env,void *opaque){
    BattleWaitContext *c=opaque;uintptr_t b=imageBase();int v=c->variant;
    uint8_t *(*serviceGet)(void *)=(void *)(b+AGMaps[v].service);
    uint8_t *volatile service=serviceGet(env);if(!service)return 0;
    c->connection=*(uintptr_t *)(service+0x10);if(!c->connection)return 0;
    uint8_t *room=*(uint8_t **)(b+AGNotesMaps[v].room_class);
    uint8_t *g=*(uint8_t **)(b+AGTurnMaps[v].arena_class);
    uint8_t *arrayClass=*(uint8_t **)(b+AGTurnMaps[v].array_class);
    c->room=room?room[0x130]:-1;
    c->arena=g?*(uint8_t **)(g+0xe8):0;c->local=g?(int8_t)g[0x266]:-1;
    c->canvas=*(uint8_t **)(b+AGNotesMaps[v].canvas);
    c->players=arrayClass?*(uint8_t **)(arrayClass+0xa0):0;
    c->projectiles=*(uint8_t **)(b+AGTurnMaps[v].projectile_class);
    c->airship=c->room==10;
    // Linked rooms contain several stages. The native actor's character byte
    // identifies balloon17; the room's area byte is not a map identifier.
    if((c->room==14||c->room==15)&&c->players){
        int count=*(int *)(c->players+0x10);
        if(count>=9&&count<=127)for(int i=8;i<count;i++){
            uint8_t *p=*(uint8_t **)(c->players+0x18+i*8);
            if(p&&p[0x16c]==17){c->airship=1;break;}
        }
    }
    return 1;
}
static int context(void *env,BattleWaitContext *c){
    return AGWheelGuard(env,readContext,c,(void *)(imageBase()+0x1300d54));
}
static int active(const BattleWaitContext *c){
    return c->arena&&c->canvas&&*(uint8_t **)(c->canvas+0xb8)==c->arena;
}
static int busy(const BattleWaitContext *c,int kind,int actor){
    if(kind==0)return c->projectiles&&((volatile uint8_t *)c->projectiles)[0x118];
    if(kind==1)return c->canvas&&((volatile uint8_t *)c->canvas)[0x13c];
    if((kind==2||kind==3)&&c->players){
        int count=*(int *)(c->players+0x10);
        if(actor>=0&&actor<count&&count<=127){
            uint8_t *p=*(uint8_t **)(c->players+0x18+actor*8);
            return p&&((volatile uint8_t *)p)[kind==2?0x167:0x14e];
        }
    }
    return 0;
}
static uint64_t watchNanos(void){
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t))return 0;
    return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;
}
static volatile uint8_t *watchFlag(const BattleWaitContext *c,int kind,int slot){
    if(kind==0)return c->projectiles?c->projectiles+0x118:0;
    if(kind==1)return c->canvas?c->canvas+0x13c:0;
    if((kind==2||kind==3)&&c->players){
        int count=*(int *)(c->players+0x10);
        if(slot>=0&&slot<count&&count<=127){
            uint8_t *p=*(uint8_t **)(c->players+0x18+slot*8);
            if(p)return p+(kind==2?0x167:0x14e);
        }
    }
    return 0;
}
__attribute__((visibility("default"))) void AGBattleAwait(void *env,void *lock,int v,int kind,int actor){
    if(!env||!lock||v<0||v>=6)return;
    BattleWaitContext c={.variant=v};
    int running=AGNativeWatchRunning(v),stillWatching=AGViewerStillWatching(v);
    int watching=running||stillWatching;
    /* SP53 replays HP/status before its final clock packet. These are a
       snapshot, not animations to wait for. The APK's syncing flag bypasses
       the same flash wait. Running becomes true only AFTER this replay;
       using it here sends the receive thread into the old indefinite wait. */
    if(watching&&(!running||!stillWatching))return;
    if(context(env,&c)<=0){
        if(!watching)AGTurnAwait(env,lock,v,kind,actor);
        return;
    }
    if(!c.airship&&!watching){
        AGTurnAwait(env,lock,v,kind,actor);
        return;
    }
    if(!active(&c))return;
    uint8_t *arena=c.arena;uintptr_t connection=c.connection;
    uint8_t *roster=c.players;
    volatile uint8_t *flag=watching?watchFlag(&c,kind,actor):0;
    uint64_t started=watching?watchNanos():0;
    if(watching)AGNativeWatchTraceWait(v,kind,actor,1);
    if(!watching){AGShipTraceWait(v,kind,actor,1);AGShipTraceTick(env,v,2);}
    // A fast B52 can finish and notify before the controller acquires its
    // monitor. Recheck the real completion flag before waiting, and after
    // each wake. Spectators additionally retain the APK's bounded recovery;
    // non-spectator battles keep their existing completion-based handling.
    while((!watching||AGViewerStillWatching(v))&&busy(&c,kind,actor)){
        /* Match the supplied APK's Wait106: a stalled animation cannot
           block the spectator receive stream indefinitely. Expiry clears
           only the same completion flag; it never grants or invents turns. */
        if(watching&&started){
            uint64_t time=watchNanos();
            if(time>=started&&time-started>=30000000000ULL){
                if(flag)*flag=0;
                AGNativeWatchTraceWait(v,kind,actor,3);
                return;
            }
        }
        void (*wait)(void *,void *,int64_t)=(void *)(imageBase()+0xaaa730);
        wait(env,lock,16);
        if(!watching)AGShipTraceTick(env,v,2);
        c=(BattleWaitContext){.variant=v};
        if(context(env,&c)<=0||!active(&c)||(!watching&&!c.airship)||c.arena!=arena||c.connection!=connection)break;
        /* A re-entered scene must not release a different roster's flag. */
        if(watching&&(kind==2||kind==3)&&(c.players!=roster||watchFlag(&c,kind,actor)!=flag))break;
    }
    if(watching)AGNativeWatchTraceWait(v,kind,actor,2);
    if(!watching)AGShipTraceWait(v,kind,actor,0);
}

