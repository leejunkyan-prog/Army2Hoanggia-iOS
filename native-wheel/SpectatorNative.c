/* SP53 snapshot adapter. Actors, bullets, impacts, terrain destruction and
 * camera are rendered by the unchanged game engine, as on the APK. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <time.h>
#include "SpectatorNative.h"
#include "Spectator.h"
#ifdef AG_WHEEL_PREVIEW
int AGNativeWatchAvailable(void){return 0;}
int AGNativeWatchFree(int v){return 0;}
int AGNativeWatchRunning(int v){return 0;}
int AGNativeWatchAngle(int v){return -1;}
int AGNativeWatchPacket(void *e,int v,const uint8_t *p,size_t n){return 0;}
int AGNativeWatchReplay(void *e,int v,int cmd,const uint8_t *p,size_t n){return 0;}
int AGNativeWatchFinishSnapshot(void *e,int v){return 0;}
int AGNativeWatchTryFinishSnapshot(void *e,int v){return 0;}
void AGNativeWatchObserve(int v,int cmd,const uint8_t *p,size_t n){}
void AGNativeWatchOption(int v,int option){}
int AGNativeWatchAux(int v){return 0;}
void AGNativeWatchSwitch(void *e,int v){}
void AGNativeWatchEnd(void *e,int v){}
int AGNativeWatchTryEnd(void *e,int v){return 1;}
void AGNativeWatchCamera(int v,int k,int c){}
int AGNativeWatchToggleCamera(int v){return 0;}
void AGNativeWatchClearCameraKeys(int v){}
void AGNativeWatchNudgeCamera(int v,int code){}
void AGNativeWatchTick(void *e,int v){}
#else
#include <mach-o/dyld.h>
#include <pthread.h>
static pthread_mutex_t watchLock=PTHREAD_MUTEX_INITIALIZER;
#include "SpectatorNativeMap.h"
#include "TurnMap.h"
#include "NotesMap.h"
#include "BossNativeMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {uint8_t *encoded;void *image;int size,width,height;uint64_t hash;} TileImage;
typedef struct {
    int active,started,prepared,snapshotComplete,v,map,width,height,bricks,next,id,x,y,solid,total,received;
    int roster,turn,first,seconds,oldWidth,oldHeight;
    int oldCamera[6];
    uint8_t *bytes,*back,*arena,*oldMap,*oldTiles,*oldBackdrop,*oldRoster;
    uint8_t oldLocal,oldBackground,oldMode,oldCameraMode,restoreCamera,oldTurn,oldFlash;
    uint8_t oldTerrainFlags[3];
    uint8_t oldArenaState[6];
    uint64_t moveAt;
    TileImage images[64];int imageCount,imagePixels;
} Watch;
static Watch watches[6];
static atomic_int cameraKeys[6],cameraNudge[6],freeCamera[6],cameraChanged[6];
static atomic_int watchOption[6];
static atomic_int auxiliary[6],running[6],watchAngle[6];
static const struct {
    uintptr_t force,team,friends,messageNew,messageInit,messageOpen;
} menuMethods[6]={
    {0x4f5d58,0x5b2ad4,0x59f38c,0x515834,0x515880,0x5158bc},
    {0x5e4778,0x69b0a0,0x688088,0x603354,0x6033a0,0x6033dc},
    {0x6c943c,0x77fd64,0x76cd4c,0x6e8018,0x6e8064,0x6e80a0},
    {0x7ae100,0x864a28,0x851a10,0x7cccdc,0x7ccd28,0x7ccd64},
    {0x892dc4,0x9496ec,0x9366d4,0x8b19a0,0x8b19ec,0x8b1a28},
    {0x977a88,0xa2e3b0,0xa1b398,0x996664,0x9966b0,0x9966ec},
};
static uintptr_t base(void){return (uintptr_t)_dyld_get_image_header(0);}
static uint8_t *global(uintptr_t a){return *(uint8_t **)(base()+a);}
static int be16(const uint8_t *p){return (int16_t)((p[0]<<8)|p[1]);}
static unsigned u16(const uint8_t *p){return (p[0]<<8)|p[1];}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3];}
static int64_t be64(const uint8_t *p){uint64_t n=0;for(int i=0;i<8;i++)n=n<<8|p[i];return (int64_t)n;}
static void *pin(void *e,void *p){return p?((void *(*)(void *,void *))(*(void ***)e)[21])(e,p):NULL;}
static void unpin(void *e,void *p){if(p)((void (*)(void *,void *))(*(void ***)e)[22])(e,p);}
static void *newVector(void *e,int capacity){
    void *volatile vector=((void *(*)(void *))(base()+0xbe3f1c))(e);
    if(vector)((void (*)(void *,void *,int))(base()+0xbe6ba0))(e,vector,capacity);
    return vector;
}
static uint8_t *actor(int v,int slot){
    uint8_t *g=global(AGTurnMaps[v].array_class);
    uint8_t *players=g?*(uint8_t **)(g+0xa0):NULL;
    if(!players||slot<0||slot>=*(int *)(players+0x10))return NULL;
    return *(uint8_t **)(players+0x18+slot*8);
}
static void placeCamera(Watch *w,int x,int y){
    uint8_t *g=global(AGSpectatorMaps[w->v].cameraClass);
    uint8_t *canvas=global(AGNotesMaps[w->v].canvas);
    if(!g||!canvas)return;
    int maxX=w->width-*(int *)(canvas+0x130),maxY=w->height-*(int *)(canvas+0x128);
    if(maxX<0)maxX=0;if(maxY<0)maxY=0;
    if(x<0)x=0;if(y<0)y=0;if(x>maxX)x=maxX;if(y>maxY)y=maxY;
    *(int *)(g+0xa4)=*(int *)(g+0xac)=x;
    *(int *)(g+0xa8)=*(int *)(g+0xb0)=y;
    *(int *)(g+0xb4)=0;*(int *)(g+0xb8)=0;
}
static void centerActor(Watch *w,int slot){
    uint8_t *g=global(AGSpectatorMaps[w->v].cameraClass);
    uint8_t *canvas=global(AGNotesMaps[w->v].canvas);
    uint8_t *p=actor(w->v,slot);
    if(!g||!canvas||!p)return;
    int h=*(int *)(canvas+0x128);
    placeCamera(w,*(int *)(p+0x114)-*(int *)(canvas+0x130)/2,*(int *)(p+0x118)-h*3/4);
    uint8_t *arena=global(AGTurnMaps[w->v].arena_class);
    uint8_t *follow=arena?*(uint8_t **)(arena+0xd8):NULL;
    if(follow)*(int *)(follow+0x20)=slot;
    g[0xbc]=1;
}
static const uint8_t arenaStateOffsets[]={0,1,2,3,4,7};
__attribute__((noinline,optnone)) static int prepare(void *e,void *opaque){
    Watch *w=opaque;int v=w->v;uintptr_t b=base();const AGSpectatorMap *m=&AGSpectatorMaps[v];
    /* The allocator performs the normal RoboVM class initialization. */
    uint8_t *a=global(AGTurnMaps[v].arena_class);
    /* The roster is installed by native cmd8 before we initialize the map
       used to start the battle. Preserve the pre-watch navigation screen. */
    void *volatile arena=NULL;
    if(!a||!*(void **)(a+0xe8)){
        arena=((void *(*)(void *))(b+m->arenaNew))(e);
        if(!arena)return 0;
        ((void (*)(void *,void *))(b+m->arenaInit))(e,arena);
        a=global(AGTurnMaps[v].arena_class);
        if(!a)return 0;
        *(void **)(a+0xe8)=arena;
    }
    uint8_t *canvas=global(AGNotesMaps[v].canvas);
    if(!a||!canvas||!*(void **)(canvas+0xb8))return 0;
    w->back=pin(e,*(void **)(canvas+0xb8));if(!w->back)return 0;
    w->oldFlash=canvas[0x13c];
    w->arena=*(void **)(a+0xe8);
    w->oldLocal=a[0x266];w->oldMode=a[0x265];w->oldMap=pin(e,*(void **)(a+0xc8));
    for(size_t i=0;i<sizeof arenaStateOffsets;i++)w->oldArenaState[i]=a[0x260+arenaStateOffsets[i]];
    uint8_t *players=global(AGTurnMaps[v].array_class);
    if(players){w->oldRoster=pin(e,*(void **)(players+0xa0));w->oldTurn=players[0xd0];}
    uint8_t *camera=global(m->cameraClass);
    if(camera){
        memcpy(w->oldCamera,camera+0xa4,sizeof w->oldCamera);
        w->oldCameraMode=camera[0xbc];w->restoreCamera=1;
    }
    uint8_t *volatile map=((void *(*)(void *))(b+m->mapNew))(e);
    if(!map)return 0;
    ((void (*)(void *,void *))(b+m->mapInit))(e,map);
    uint8_t *g=global(AGBossNativeMaps[v].mapClass);
    if(!g)return 0;
    w->oldTiles=pin(e,*(void **)(g+0xb8));
    w->oldBackdrop=pin(e,*(void **)(g+0xc8));
    w->oldWidth=*(int *)(g+0xd8);w->oldHeight=*(int *)(g+0xdc);
    w->oldBackground=g[0xe0];memcpy(w->oldTerrainFlags,g+0xe1,sizeof w->oldTerrainFlags);
    w->prepared=1;
    *(void **)(a+0xc8)=map;*(int *)(map+0x10)=w->map;
    *(int *)(g+0xd8)=w->width;*(int *)(g+0xdc)=w->height;
    void *volatile tiles=newVector(e,w->bricks);
    if(!tiles)return 0;
    *(void **)(g+0xb8)=tiles;g[0xe0]=0;
    return 1;
}
__attribute__((noinline,optnone)) static int buildTile(void *e,void *opaque){
    Watch *w=opaque;uintptr_t b=base();void **jni=*(void ***)e;
    uint64_t hash=1469598103934665603ULL;
    for(int i=0;i<w->total;i++)hash=(hash^w->bytes[i])*1099511628211ULL;
    void *volatile image=NULL;int width=0,height=0;
    for(int i=0;i<w->imageCount;i++){
        TileImage *c=&w->images[i];
        if(c->size==w->total&&c->hash==hash&&!memcmp(c->encoded,w->bytes,w->total)){
            image=c->image;width=c->width;height=c->height;break;
        }
    }
    if(!image){
        void *volatile raw=((void *(*)(void *,int))jni[176])(e,w->total);
        if(!raw)return 0;
        ((void (*)(void *,void *,int,int,const uint8_t *))jni[208])(e,raw,0,w->total,w->bytes);
        image=((void *(*)(void *,void *,int,int))(b+0xc46e04))(e,raw,0,w->total);
        ((void (*)(void *,void *))jni[23])(e,raw);
        if(!image)return 0;
        width=((int (*)(void *,void *))(b+0x1c61b0))(e,image);
        height=((int (*)(void *,void *))(b+0x1c61a0))(e,image);
        if(width<1||height<1||width>4096||height>4096||(int64_t)width*height>4000000)return 0;
        if(w->imageCount<64&&w->imagePixels+width*height<=4000000){
            uint8_t *copy=malloc(w->total);void *root=copy?pin(e,image):NULL;
            if(root){memcpy(copy,w->bytes,w->total);w->images[w->imageCount++]=(TileImage){copy,root,w->total,width,height,hash};w->imagePixels+=width*height;}
            else free(copy);
        }
    }
    if(width<1||height<1||width>4096||height>4096||(int64_t)width*height>4000000)return 0;
    const AGBossNativeMap *m=&AGBossNativeMaps[w->v];
    uint8_t *volatile tile=((void *(*)(void *))(b+m->tileNew))(e);
    if(!tile)return 0;
    ((void (*)(void *,void *,int64_t,int,int,void *,int))(b+m->tileInit))(e,tile,w->id,w->x,w->y,NULL,w->solid);
    /* Image is immutable. Destruction edits tile+0x10 and replaces that
       tile's rendered image; each tile must keep its own mutable pixels. */
    void *volatile pixels=((void *(*)(void *,int))(b+0x12e7d28))(e,width*height);
    if(!pixels)return 0;
    ((void (*)(void *,void *,void *,int,int,int,int,int,int))(b+0x1c61a4))(e,image,pixels,0,width,0,0,width,height);
    *(void **)(tile+0x10)=pixels;*(void **)(tile+0x18)=image;
    *(int *)(tile+0x28)=width;*(int *)(tile+0x2c)=height;
    uint8_t *g=global(m->mapClass);
    ((void (*)(void *,void *,void *))(b+0x1dfcac))(e,*(void **)(g+0xb8),tile);
    return 1;
}
typedef struct {Watch *w;int clock,first;int64_t x[8],y[8],hp[8];} Start;
__attribute__((noinline,optnone)) static int start(void *e,void *opaque){
    Start *s=opaque;Watch *w=s->w;int v=w->v;uintptr_t b=base();
    const AGSpectatorMap *m=&AGSpectatorMaps[v];uint8_t *g=global(AGTurnMaps[v].arena_class);
    /* On first login there is no battle actor array yet. Native arena.start
       creates it. cmd8 supplies room-member data, not that actor array; use
       the same native capacity getter as arena.start instead of requiring
       an array left over from a previous battle. */
    int slots=((int (*)(void *))(b+m->slots))(e);
    if(!g||!w->arena||slots<8||slots>127)return 0;
    void *volatile arrays[3];const int64_t *data[3]={s->x,s->y,s->hp};
    for(int i=0;i<3;i++){
        arrays[i]=((void *(*)(void *,int))(b+0x12e7d88))(e,slots);
        if(!arrays[i])return 0;
        int64_t *values=(int64_t *)((uint8_t *)arrays[i]+0x18);
        memcpy(values,data[i],8*sizeof *values);
        for(int slot=8;slot<slots;slot++)values[slot]=i==0?-1:0;
    }
    g[0x261]=0;
    // The native dispatcher addresses a roster slot here even while drawing
    // a replay. Keep it in bounds, with the overlay owning all battle input.
    g[0x266]=s->first;
    ((void (*)(void *,void *,int,void *,void *,void *,int64_t))(b+m->start))
        (e,*(void **)(g+0xe8),s->clock,arrays[0],arrays[1],arrays[2],0);
    g[0x266]=s->first;
    /* cmd8 was dispatched through the game parser. Validate the actual
       combat roster before showing the scene. */
    for(int i=0;i<8;i++){
        if(s->x[i]==-1)continue;
        uint8_t *player=actor(v,i);
        if(!player)return 0;
        // Native start initializes max HP from this array. Keep the
        // current HP delivered by the subsequent authoritative cmd51.
        *(int *)(player+0x114)=(int)s->x[i];
        *(int *)(player+0x118)=(int)s->y[i];
        *(int *)(player+0x11c)=(int)s->x[i];
        *(int *)(player+0x124)=(int)s->y[i];
    }
    w->first=s->first;
    w->seconds=s->clock;
    centerActor(w,s->first);
    uint8_t *arena=w->arena;
    *(void **)(arena+0x18)=NULL;*(void **)(arena+0x20)=NULL;*(void **)(arena+0x28)=NULL;
    w->started=1;
    atomic_store(&freeCamera[v],0);AGNativeWatchClearCameraKeys(v);
    uint8_t *viewed=actor(v,s->first);
    int angle=viewed?*(int *)(viewed+0xa4):-1;
    atomic_store(&watchAngle[v],angle>=0&&angle<360?angle:-1);
    return 1;
}
static int show(void *e,void *opaque){
    Watch *w=opaque;int v=w->v;
    uint8_t *canvas=global(AGNotesMaps[v].canvas);
    if(!canvas||!w->arena||!AGViewerStillWatching(v))return 0;
    if(*(void **)(canvas+0xb8)==w->arena)return 1;
    /* cmd8 legitimately activates the room after SP3 saved the area list
       as back. The APK presents after SP5 without requiring that old screen
       to remain current. StillWatching already rejects canceled/ended views. */
    uintptr_t b=base();
    ((void (*)(void *))(b+AGBossNativeMaps[v].resetInput))(e);
    ((void (*)(void *,void *,void *))(b+AGSpectatorMaps[v].show))(e,w->arena,w->back);
    return *(void **)(canvas+0xb8)==w->arena;
}
static int restore(void *e,void *opaque){
    Watch *w=opaque;int v=w->v;uint8_t *a=global(AGTurnMaps[v].arena_class);
    uint8_t *g=global(AGBossNativeMaps[v].mapClass);
    uint8_t *canvas=global(AGNotesMaps[v].canvas);
    if(w->started&&w->back&&canvas&&*(void **)(canvas+0xb8)!=w->back){
        ((void (*)(void *,void *))(base()+AGSpectatorMaps[v].restore))(e,w->back);
        ((void (*)(void *))(base()+AGBossNativeMaps[v].resetInput))(e);
    }
    if(canvas){
        canvas[0x13c]=w->oldFlash;
        /* A force/message/result dialog opened while watching must not
           cover the area list after the server's end-of-match packet. */
        if(w->started)*(void **)(canvas+0x108)=NULL;
    }
    if(a){
        a[0x266]=w->oldLocal;a[0x265]=w->oldMode;*(void **)(a+0xc8)=w->oldMap;
        for(size_t i=0;i<sizeof arenaStateOffsets;i++)a[0x260+arenaStateOffsets[i]]=w->oldArenaState[i];
    }
    if(g){
        *(void **)(g+0xb8)=w->oldTiles;*(void **)(g+0xc8)=w->oldBackdrop;
        *(int *)(g+0xd8)=w->oldWidth;*(int *)(g+0xdc)=w->oldHeight;
        g[0xe0]=w->oldBackground;memcpy(g+0xe1,w->oldTerrainFlags,sizeof w->oldTerrainFlags);
    }
    uint8_t *players=global(AGTurnMaps[v].array_class);
    if(players){*(void **)(players+0xa0)=w->oldRoster;players[0xd0]=w->oldTurn;}
    uint8_t *camera=global(AGSpectatorMaps[v].cameraClass);
    if(camera&&w->restoreCamera){memcpy(camera+0xa4,w->oldCamera,sizeof w->oldCamera);camera[0xbc]=w->oldCameraMode;}
    return 1;
}
static int guard(void *e,int (*fn)(void *,void *),void *j){return AGWheelGuard(e,fn,j,(void *)(base()+0x1300d54));}
typedef struct {int v;uint8_t *player;int64_t hp;} ReplayHP;
static int replayHP(void *e,void *opaque){
    ReplayHP *j=opaque;
    static const uintptr_t death[6]={0x5978c0,0x6807ec,0x7654b0,0x84a174,0x92ee38,0xa13afc};
    /* The APK's syncing path applies state without damage text, HP flash,
       animation waits or clock changes. Keep the normal death cleanup. */
    *(int64_t *)(j->player+0x68)=j->hp;
    if(j->hp<=0)((void (*)(void *,void *))(base()+death[j->v]))(e,j->player);
    return 1;
}
int AGNativeWatchReplay(void *e,int v,int cmd,const uint8_t *p,size_t n){
    if(!e||v<0||v>=6||cmd!=51||!p||n!=10)return 0;
    pthread_mutex_lock(&watchLock);
    Watch *w=&watches[v];int consumed=0;
    if(w->started&&AGViewerStillWatching(v)&&!AGNativeWatchRunning(v)){
        uint8_t *player=actor(v,p[0]);
        if(player){ReplayHP j={v,player,be64(p+1)};consumed=guard(e,replayHP,&j)>0;}
    }
    pthread_mutex_unlock(&watchLock);
    return consumed;
}
typedef struct {int v,option;uint8_t *arena;} Menu;
__attribute__((noinline,optnone)) static int applyOption(void *e,void *opaque){
    Menu *j=opaque;int v=j->v;uintptr_t b=base();
    if(j->option==5){
        void *volatile message=((void *(*)(void *))(b+menuMethods[v].messageNew))(e);
        ((void (*)(void *,void *,void *))(b+menuMethods[v].messageInit))(e,message,j->arena);
        ((void (*)(void *,void *))(b+menuMethods[v].messageOpen))(e,message);
    }else{
        uintptr_t address=j->option==1?menuMethods[v].force:j->option==3?menuMethods[v].team:menuMethods[v].friends;
        ((void (*)(void *,void *))(b+address))(e,NULL);
    }
    return 1;
}
static int switchPB(void *e,void *opaque){
    ((void (*)(void *,int))(base()+0x1f3d20))(e,*(int *)opaque);
    return 1;
}
void AGNativeWatchSwitch(void *e,int v){if(v>=0&&v<6)guard(e,switchPB,&v);}
int AGNativeWatchAvailable(void){return 1;}
int AGNativeWatchFree(int v){return v>=0&&v<6&&atomic_load(&freeCamera[v]);}
int AGNativeWatchAux(int v){return v>=0&&v<6&&atomic_load(&auxiliary[v]);}
int AGNativeWatchRunning(int v){return v>=0&&v<6&&atomic_load(&running[v]);}
int AGNativeWatchAngle(int v){return AGNativeWatchRunning(v)?atomic_load(&watchAngle[v]):-1;}
static void endNative(void *e,int v){
    if(v<0||v>=6)return;Watch *w=&watches[v];
    if(w->prepared)guard(e,restore,w);
    for(int i=0;i<w->imageCount;i++){unpin(e,w->images[i].image);free(w->images[i].encoded);}
    unpin(e,w->back);unpin(e,w->oldMap);unpin(e,w->oldTiles);
    unpin(e,w->oldBackdrop);unpin(e,w->oldRoster);
    free(w->bytes);memset(w,0,sizeof *w);
    atomic_store(&running[v],0);atomic_store(&watchAngle[v],-1);
    atomic_store(&freeCamera[v],0);AGNativeWatchClearCameraKeys(v);
    atomic_store(&cameraChanged[v],0);atomic_store(&watchOption[v],0);atomic_store(&auxiliary[v],0);
}
typedef struct {Watch *w;int seconds;} Clock;
static int resetClock(void *e,void *opaque){
    Clock *j=opaque;int v=j->w->v;uint8_t *a=global(AGTurnMaps[v].arena_class);
    void *clock=a?*(void **)(a+0x110):NULL;if(!clock)return 0;
    const AGSpectatorMap *m=&AGSpectatorMaps[v];
    ((void (*)(void *,void *,int))(base()+m->clockSet))(e,clock,j->seconds);
    ((void (*)(void *,void *))(base()+m->clockReset))(e,clock);
    return 1;
}
static int finishSnapshot(void *e,Watch *w){
    if(!w->started||!w->snapshotComplete)return 0;
    Clock clock={w,w->seconds};
    if(guard(e,resetClock,&clock)<=0)return 0;
    if(!AGNativeWatchRunning(w->v)){
        /* Snapshot HP/status is state, not a participant flash animation.
           Clear its leftover flag only after the protocol barrier. */
        uint8_t *canvas=global(AGNotesMaps[w->v].canvas);
        if(canvas)canvas[0x13c]=0;
        if(w->turn>=0)centerActor(w,w->turn);
        if(guard(e,show,w)<=0)return 0;
        atomic_store(&running[w->v],1);
    }
    return 1;
}
static int packetNative(void *e,int v,const uint8_t *p,size_t n){
    if(v<0||v>=6||n<4)return 0;Watch *w=&watches[v];
    if(p[3]==3){
        if(n!=21||w->active||!u16(p+15)||!u16(p+17)||u16(p+19)>4096)return 0;
        *w=(Watch){.active=1,.v=v,.map=p[14],.width=u16(p+15),.height=u16(p+17),.bricks=u16(p+19),.turn=-1,.first=-1};
        return guard(e,prepare,w)>0;
    }
    if(!w->active)return 0;
    if(p[3]==4){
        if(w->started||n<25)return 0;
        int index=u16(p+4),id=u32(p+6),x=be16(p+10),y=be16(p+12),solid=p[14];
        uint32_t total=u32(p+15),offset=u32(p+19),size=u16(p+23);
        if(index!=w->next||index>=w->bricks||!total||total>8000000||!size||size>24000||n!=25+size||offset>total||size>total-offset)return 0;
        if(!offset){if(w->bytes)return 0;w->bytes=malloc(total);if(!w->bytes)return 0;w->total=total;w->received=0;w->id=id;w->x=x;w->y=y;w->solid=solid;}
        if(!w->bytes||w->total!=(int)total||offset!=(unsigned)w->received||w->id!=id||w->x!=x||w->y!=y||w->solid!=solid)return 0;
        memcpy(w->bytes+offset,p+25,size);w->received+=size;
        if(w->received==w->total){if(guard(e,buildTile,w)<=0)return 0;free(w->bytes);w->bytes=NULL;w->next++;}
        return 1;
    }
    if(p[3]==5){
        if(w->started||!w->roster||w->bytes||w->next!=w->bricks||n<21)return 0;
        Start s={.w=w,.clock=p[4],.first=-1};size_t pos=5;
        for(int i=0;i<8;i++){if(n-pos<2)return 0;s.x[i]=be16(p+pos);pos+=2;if(s.x[i]==-1)continue;if(n-pos<10)return 0;s.y[i]=be16(p+pos);s.hp[i]=be64(p+pos+2);pos+=10;if(s.first<0)s.first=i;}
        if(pos!=n||s.first<0)return 0;
        /* Match the working APK: present after actors/terrain are ready,
           before the following HP/status/clock replay. Deferring this to
           SP7 lets those native handlers wait on a scene still in the room. */
        if(guard(e,start,&s)<=0)return 0;
        return guard(e,show,w)>0;
    }
    if(p[3]==7){
        if(n!=5||!w->started)return 0;
        w->seconds=p[4];w->snapshotComplete=1;
        return finishSnapshot(e,w);
    }
    return 0;
}
static int direction(int code){
    return code==-3||code=='4'?1:code==-4||code=='6'?2:code==-1||code=='2'?4:code==-2||code=='8'?8:0;
}
void AGNativeWatchCamera(int v,int kind,int code){
    if(v<0||v>=6)return;
    int bit=direction(code);
    if(kind==0&&bit)atomic_fetch_or(&cameraKeys[v],bit);else if(kind==1&&bit)atomic_fetch_and(&cameraKeys[v],~bit);
}
int AGNativeWatchToggleCamera(int v){
    if(!AGNativeWatchRunning(v))return 0;
    AGNativeWatchClearCameraKeys(v);
    int free=atomic_fetch_xor(&freeCamera[v],1)^1;
    atomic_store(&cameraChanged[v],1);
    return free;
}
void AGNativeWatchClearCameraKeys(int v){
    if(v>=0&&v<6){atomic_store(&cameraKeys[v],0);atomic_store(&cameraNudge[v],0);}
}
void AGNativeWatchNudgeCamera(int v,int code){
    if(AGNativeWatchFree(v))atomic_fetch_or(&cameraNudge[v],direction(code));
}
static void tickNative(void *e,int v){
    if(!AGNativeWatchRunning(v))return;Watch *w=&watches[v];
    uint8_t *canvas=global(AGNotesMaps[v].canvas),*arenaClass=global(AGTurnMaps[v].arena_class);
    uint8_t *arena=arenaClass?*(uint8_t **)(arenaClass+0xe8):NULL;
    if(!canvas||!arena)return;
    int option=atomic_exchange(&watchOption[v],0);
    if(option){
        Menu j={v,option,arena};
        if(guard(e,applyOption,&j)>0&&option!=3)atomic_store(&auxiliary[v],1);
    }
    if(AGNativeWatchAux(v)){
        if(*(void **)(canvas+0xb8)!=arena||*(void **)(canvas+0x108))return;
        atomic_store(&auxiliary[v],0);
    }
    uint8_t *g=global(AGSpectatorMaps[v].cameraClass);if(!g)return;
    if(atomic_exchange(&cameraChanged[v],0)&&!atomic_load(&freeCamera[v]))
        centerActor(w,w->turn>=0?w->turn:w->first);
    if(!atomic_load(&freeCamera[v]))return;
    g[0xbc]=0;*(int *)(g+0xb4)=0;*(int *)(g+0xb8)=0;
    if(!(atomic_load(&cameraKeys[v])||atomic_load(&cameraNudge[v]))){w->moveAt=0;return;}
    struct timespec clock;clock_gettime(CLOCK_MONOTONIC,&clock);
    uint64_t now=(uint64_t)clock.tv_sec*1000000000+(uint64_t)clock.tv_nsec;
    if(w->moveAt&&now-w->moveAt<15000000)return;
    w->moveAt=now;
    int keys=atomic_load(&cameraKeys[v])|atomic_exchange(&cameraNudge[v],0);
    int dx=((keys&2)!=0)-((keys&1)!=0),dy=((keys&8)!=0)-((keys&4)!=0);
    int x=*(int *)(g+0xa4)+dx*8,y=*(int *)(g+0xa8)+dy*8;
    placeCamera(w,x,y);
}
void AGNativeWatchEnd(void *e,int v){pthread_mutex_lock(&watchLock);endNative(e,v);pthread_mutex_unlock(&watchLock);}
int AGNativeWatchTryEnd(void *e,int v){
    if(pthread_mutex_trylock(&watchLock))return 0;
    endNative(e,v);pthread_mutex_unlock(&watchLock);return 1;
}
int AGNativeWatchPacket(void *e,int v,const uint8_t *p,size_t n){pthread_mutex_lock(&watchLock);int ok=packetNative(e,v,p,n);pthread_mutex_unlock(&watchLock);return ok;}
int AGNativeWatchFinishSnapshot(void *e,int v){
    if(v<0||v>=6)return 0;
    pthread_mutex_lock(&watchLock);
    int ok=finishSnapshot(e,&watches[v]);
    pthread_mutex_unlock(&watchLock);
    return ok;
}
int AGNativeWatchTryFinishSnapshot(void *e,int v){
    if(v<0||v>=6||pthread_mutex_trylock(&watchLock))return 0;
    int ok=finishSnapshot(e,&watches[v]);
    pthread_mutex_unlock(&watchLock);
    return ok;
}
void AGNativeWatchObserve(int v,int cmd,const uint8_t *p,size_t n){
    if(v<0||v>=6||!p)return;
    pthread_mutex_lock(&watchLock);
    Watch *w=&watches[v];
    if(w->active&&cmd==8&&!w->started&&n>=42)w->roster=1;
    /* SP7 is the normal end-of-snapshot barrier. Legacy servers can omit
       it, but a complete live move/shot also proves replay has ended.
       Elapsed render time cannot establish this ordering. */
    if(w->started&&((cmd==21&&n==5)||((cmd==22||cmd==84)&&n>=10)))
        w->snapshotComplete=1;
    if(w->started&&cmd==24&&n>=1&&p[0]<127){
        w->turn=p[0];
        if(!AGNativeWatchRunning(v)&&n==2)w->seconds=p[1];
    }
    if(w->started&&(cmd==22||cmd==84)&&n>=10&&p[0]<=1)
        atomic_store(&watchAngle[v],(be16(p+8)%360+360)%360);
    pthread_mutex_unlock(&watchLock);
}
void AGNativeWatchOption(int v,int option){
    if(v>=0&&v<6&&(option==1||option==3||option==4||option==5))atomic_store(&watchOption[v],option);
}
void AGNativeWatchTick(void *e,int v){if(pthread_mutex_trylock(&watchLock))return;tickNative(e,v);pthread_mutex_unlock(&watchLock);}
#endif


