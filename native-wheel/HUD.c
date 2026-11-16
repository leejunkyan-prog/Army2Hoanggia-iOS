#include "HUD.h"
#include "NotesMap.h"
#include "TurnMap.h"
#include "SpectatorNative.h"
#include <mach-o/dyld.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <limits.h>
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {uintptr_t connection,arena,actors[128];int ranks[128],caps[128],w[128],h[128];
 uint64_t serial;double started;int seconds,lastFrame,travel;size_t length;uint16_t text[AGHUDTextLimit+1];} HUDState;
static HUDState states[6];static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static uintptr_t base(void){return (uintptr_t)_dyld_get_image_header(0);}
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec/1e9;}
static uint8_t *global(uintptr_t p){return *(void **)(base()+p);}
static uintptr_t connection(int v){
 static const uintptr_t slots[]={0x207b870,0x20ab650,0x20d9350,0x2107040,0x2134d30,0x2162a20};
 uint8_t *c=global(slots[v]),*s=c?*(void **)(c+0xa0):NULL;return s?*(uintptr_t *)(s+0x10):0;
}
static uintptr_t arena(int v){uint8_t *g=global(AGTurnMaps[v].arena_class);return g?*(uintptr_t *)(g+0xe8):0;}
static uint8_t *roster(int v){uint8_t *g=global(AGTurnMaps[v].array_class);return g?*(void **)(g+0xa0):NULL;}
static uint8_t *at(uint8_t *a,int slot){int n=a?*(int *)(a+0x10):0;return slot>=0&&slot<n&&n<=128?*(void **)(a+0x18+slot*8):NULL;}
static void clearRanks(HUDState *s){memset(s->actors,0,sizeof s->actors);memset(s->ranks,0,sizeof s->ranks);memset(s->caps,0,sizeof s->caps);memset(s->w,0,sizeof s->w);memset(s->h,0,sizeof s->h);s->arena=0;}
static HUDState *state(int v){HUDState *s=&states[v];uintptr_t c=connection(v);if(s->connection!=c){uint64_t serial=s->serial+1;memset(s,0,sizeof *s);s->connection=c;s->serial=serial;}return s;}
int AGHUDReceive(void *env,void *message,int v){
 if(!env||!message||v<0||v>=6)return 0;uint8_t *m=message;int cmd=*(int8_t *)(m+0x30);
 if(cmd==3||cmd==20){pthread_mutex_lock(&lock);HUDState *s=state(v);clearRanks(s);if(cmd==3){s->length=0;s->serial++;}pthread_mutex_unlock(&lock);return 0;}
 if(cmd!=-116&&cmd!=-121)return 0;
 uint8_t *in=*(void **)(m+0x20),*a=in?*(void **)(in+0x10):NULL;
 if(!a)return cmd==-116;
 int cap=*(int *)(a+0x10),end=*(int *)(in+0x18),pos=*(int *)(in+0x20);
 if(pos<0||end<pos||end>cap||end-pos>65535)return cmd==-116;
 const uint8_t *bytes=a+0x14+pos;size_t n=(size_t)(end-pos);
 if(cmd==-121&&(!n||(bytes[0]!=2&&bytes[0]!=4)))return 0;
 AGHUDPacket *packet=malloc(sizeof *packet);if(!packet)return 1;
 if(AGHUDParse(cmd,bytes,n,packet)){
  pthread_mutex_lock(&lock);HUDState *s=state(v);
  if(packet->kind==1){s->length=packet->length;memcpy(s->text,packet->text,(packet->length+1)*2);s->started=now();s->seconds=packet->seconds;s->travel=0;
   uint8_t *c=global(AGNotesMaps[v].canvas);s->lastFrame=c?*(int *)(c+0x124):0;s->serial++;
  }else if(packet->kind==4)clearRanks(s);
  else{
   int slot=packet->slot;uintptr_t owner=arena(v);if(s->arena&&s->arena!=owner)clearRanks(s);s->arena=owner;
   s->ranks[slot]=packet->rank;s->caps[slot]=packet->maximum;s->w[slot]=s->h[slot]=0;
   uint8_t *p=at(roster(v),slot);s->actors[slot]=(uintptr_t)p;
   /* Same authoritative maximum that MarketNative79.rankHP applies in APK. */
   if(p)*(int64_t *)(p+0x70)=packet->maximum;
  }
  pthread_mutex_unlock(&lock);
 }
 free(packet);return 1; /* Only the two owned -121 subtypes are consumed. */
}
typedef struct {int tx,ty,x,y,w,h;uint8_t color[16];} GraphicsState;
static GraphicsState save(uint8_t *g){GraphicsState s={.tx=g[0x50]?*(int *)(g+0x48):0,.ty=g[0x50]?*(int *)(g+0x4c):0,.x=*(int *)(g+0x38),.y=*(int *)(g+0x3c),.w=*(int *)(g+0x40),.h=*(int *)(g+0x44)};memcpy(s.color,g+0x28,16);return s;}
static void translate(void *e,uint8_t *g,int x,int y){((void (*)(void *,void *,int,int))(base()+0x1c619c))(e,g,x,y);}
static void clip(void *e,uint8_t *g,int x,int y,int w,int h){((void (*)(void *,void *,int,int,int,int))(base()+0x1c6190))(e,g,x,y,w,h);}
static void restore(void *e,uint8_t *g,GraphicsState s){translate(e,g,s.tx-(g[0x50]?*(int *)(g+0x48):0),s.ty-(g[0x50]?*(int *)(g+0x4c):0));clip(e,g,s.x-s.tx,s.y-s.ty,s.w,s.h);memcpy(g+0x28,s.color,16);}
static void *font(void *e,int v){return ((void *(*)(void *))(base()+AGNotesMaps[v].font_get+0x3c))(e);}
static void draw(void *e,int v,uint8_t *g,void *f,void *s,int x,int y,int anchor){((void (*)(void *,void *,void *,void *,int,int,int))(base()+AGNotesMaps[v].font))(e,f,g,s,x,y,anchor);}
static void label(void *e,int v,uint8_t *g,void *f,const uint16_t *text,int n,int x,int y){void **jni=*(void ***)e;void *s=((void *(*)(void *,const uint16_t *,int))jni[163])(e,text,n);if(s){draw(e,v,g,f,s,x,y,2);((void (*)(void *,void *))jni[23])(e,s);}}
typedef struct {int v,width,height,travel;uint64_t serial;size_t length;uint8_t *g;uint16_t text[];} MarqueePaint;
static int marquee(void *env,void *opaque){
 MarqueePaint *j=opaque;void **jni=*(void ***)env;void *f=font(env,j->v);if(!f)return 0;
 void *text=((void *(*)(void *,const uint16_t *,int))jni[163])(env,j->text,(int)j->length);if(!text)return 0;
 int width=((int (*)(void *,void *,void *))(base()+AGNotesMaps[j->v].font+0x1f0))(env,f,text);
 if(width>=0&&j->travel>=(int64_t)width+j->width){pthread_mutex_lock(&lock);HUDState *s=&states[j->v];if(s->serial==j->serial)s->length=0;pthread_mutex_unlock(&lock);}
 else{GraphicsState old=save(j->g);translate(env,j->g,-old.tx,-old.ty);clip(env,j->g,0,0,j->width,j->height<17?j->height:17);draw(env,j->v,j->g,f,text,j->width-j->travel,1,0);restore(env,j->g,old);}
 ((void (*)(void *,void *))jni[23])(env,text);return 1;
}
__attribute__((visibility("default"))) void AGHUDPaint(void *env,uint8_t *graphics,int v){
 if(!env||!graphics||v<0||v>=6)return;uint8_t *c=global(AGNotesMaps[v].canvas);if(!c)return;
 int width=*(int *)(c+0x130),height=*(int *)(c+0x128);if(width<1||width>4096||height<1||height>4096)return;
 pthread_mutex_lock(&lock);HUDState *s=state(v);double elapsed=now()-s->started;
 if(!s->length||elapsed<0||(s->seconds>0&&elapsed>=s->seconds)){if(s->seconds>0&&elapsed>=s->seconds)s->length=0;pthread_mutex_unlock(&lock);return;}
 int frame=*(int *)(c+0x124),delta=frame-s->lastFrame;if(delta<0)delta+=10001;if(delta<0||delta>10000)delta=0;s->lastFrame=frame;
 if(s->travel<=INT_MAX-delta)s->travel+=delta;
 MarqueePaint *j=malloc(sizeof *j+s->length*2);if(j){*j=(MarqueePaint){.v=v,.g=graphics,.width=width,.height=height,.travel=s->travel,.serial=s->serial,.length=s->length};memcpy(j->text,s->text,s->length*2);}
 pthread_mutex_unlock(&lock);if(j){GraphicsState saved=save(graphics);AGWheelGuard(env,marquee,j,(void *)(base()+0x1300d54));restore(env,graphics,saved);free(j);}
}
__attribute__((visibility("default"))) void AGHUDCanvasPaint(void *env,void *canvas,uint8_t *g,int v,void (*original)(void *,void *,void *)){
 AGNativeWatchRenderFrame(env,v);original(env,canvas,g);AGHUDPaint(env,g,v);
}
typedef struct RankPaint {uint8_t *p,*g;int v,slot,rank,cap,w,h,minX,minY,maxX,maxY,collect;uint64_t time;GraphicsState original;void (*native)(void *,void *,void *);} RankPaint;
static pthread_key_t paintKey;static pthread_once_t keyOnce=PTHREAD_ONCE_INIT;static _Atomic int keyReady;
static void createKey(void){if(!pthread_key_create(&paintKey,NULL))atomic_store(&keyReady,1);}
static RankPaint *current(void){return atomic_load(&keyReady)?pthread_getspecific(paintKey):NULL;}
__attribute__((visibility("default"))) int AGHUDSkipBar(void *env,uint8_t *p,uint8_t *g,int v){(void)env;RankPaint *j=current();return j&&j->collect&&j->p==p&&j->g==g&&j->v==v;}
/* Called by audited graphics trampolines. Integer stack arguments use the
   Darwin ARM64 packed ABI. Original image/region geometry is left intact. */
__attribute__((visibility("default"))) void AGHUDImage(uint64_t *r,int region){
 RankPaint *j=current();if(!j||!j->collect||j->g!=(void *)r[1]||!r[2])return;
 uint8_t *image=(void *)r[2];int w,h,x,y,anchor;
 if(region){w=(int)r[5];h=(int)r[6];if((int)r[7]>=4){int t=w;w=h;h=t;}const int32_t *args=(const int32_t *)(r+8);x=args[0];y=args[1];anchor=args[2];}
 else{w=*(int *)(image+0x20);h=*(int *)(image+0x24);x=(int)r[3];y=(int)r[4];anchor=(int)r[5];}
 if(w<=0||h<=0||w>16384||h>16384)return;
 if(anchor&8)x-=w;else if(anchor&1)x-=w/2;if(anchor&32)y-=h;else if(anchor&2)y-=h/2;
 x+=(j->g[0x50]?*(int *)(j->g+0x48):0)-j->original.tx;y+=(j->g[0x50]?*(int *)(j->g+0x4c):0)-j->original.ty;
 if(x<j->minX)j->minX=x;if(y<j->minY)j->minY=y;if(x+w>j->maxX)j->maxX=x+w;if(y+h>j->maxY)j->maxY=y+h;
 j->collect=0;void *tint=AGRankImage((void *)r[0],image,j->rank,0,0);j->collect=1;if(tint)r[2]=(uintptr_t)tint;
}
static void color(void *e,uint8_t *g,int rgb){((void (*)(void *,void *,int))(base()+0x1c6194))(e,g,rgb);}
static void rect(void *e,uint8_t *g,int x,int y,int w,int h,int fill){((void (*)(void *,void *,int,int,int,int))(base()+(fill?0x1c6170:0x1c614c)))(e,g,x,y,w,h);}
static int ranked(void *env,void *opaque){
 RankPaint *j=opaque;int x=*(int *)(j->p+0x114),y=*(int *)(j->p+0x118);uint8_t *clazz=global(AGTurnMaps[j->v].player_class);void *pow=clazz?*(void **)(clazz+0x148):NULL;
 int fw=j->w>0?j->w+4:28,fh=j->h>0?j->h+4:32;fw=(fw+7)/8*8;fh=(fh+7)/8*8;if(fw>256)fw=256;if(fh>256)fh=256;
 void *flame=pow?AGRankImage(env,pow,j->rank,fw,fh):NULL;
 if(flame)((void (*)(void *,void *,void *,int,int,int,int,int,int,int,int))(base()+0x1c6150))(env,j->g,flame,0,(int)(j->time/(j->rank==1?105:j->rank==2?90:75)%4)*fh,fw,fh,0,x,y+3,33);
 j->collect=1;j->native(env,j->p,j->g);j->collect=0;
 restore(env,j->g,j->original);
 if(j->maxX>=j->minX&&j->maxY>=j->minY){int w=j->maxX-j->minX,h=y-j->minY;if(w>180)w=180;if(h>180)h=180;if(w>j->w)j->w=w;if(h>j->h)j->h=h;}
 int top=j->maxY>=j->minY?j->minY:y-(j->h>40?j->h:40),barY=top-26,bw=j->w+j->rank*6,bh=j->rank+5;if(bw<52)bw=52;if(bw>90)bw=90;
 int64_t hp=*(int64_t *)(j->p+0x68);if(hp<=0)return 1;int fill=(int)(hp>j->cap?bw-2:hp*(bw-2)/j->cap),left=x-bw/2;
 color(env,j->g,1186347);rect(env,j->g,left-3,barY-3,bw+6,bh+6,1);
 color(env,j->g,AGRankColor(j->rank));rect(env,j->g,left-1,barY-1,bw+1,bh+1,0);rect(env,j->g,left+1,barY+1,fill,bh-2,1);
 color(env,j->g,j->rank==1?13760511:j->rank==2?15719167:14286821);if(fill>0)rect(env,j->g,left+1,barY+1,fill,1,1);
 if(j->rank>=2)rect(env,j->g,left-3,barY-3,bw+5,bh+5,0);
 if(j->rank==3)for(int row=-2;row<=bh+2;row++){int distance=abs(row-bh/2),span=5-distance*5/(bh/2+2);if(span>0){rect(env,j->g,left-4-span,barY+row,span,1,1);rect(env,j->g,left+bw+4,barY+row,span,1,1);}}
 void *f=font(env,j->v);if(f){
  static const uint16_t titles[3][9]={{'T','i','n','h',' ','a','n','h',0},{'T','h',0x1ee7,' ','l',0x129,'n','h',0},{'C','a','o',' ','t','h',0x1ee7,0}};
  label(env,j->v,j->g,f,titles[j->rank-1],j->rank==3?7:8,x,top-12);
  char ascii[48];int n=snprintf(ascii,sizeof ascii,"%lld/%d",(long long)hp,j->cap);uint16_t text[48];for(int i=0;i<n;i++)text[i]=(uint8_t)ascii[i];label(env,j->v,j->g,f,text,n,x,barY-17);
 }
 return 1;
}
int AGRankPaintActor(void *env,uint8_t *p,uint8_t *g,int v,void (*native)(void *,void *,void *)){
 if(!env||!p||!g||!native||v<0||v>=6||*(int64_t *)(p+0x68)<=0||p[0x16f]==5)return 0;
 uint8_t *c=global(AGNotesMaps[v].canvas);uintptr_t owner=arena(v);if(!c||!owner||*(uintptr_t *)(c+0xb8)!=owner)return 0;
 uint8_t *a=roster(v);int slot=p[0x16b];if(at(a,slot)!=p)return 0;
 pthread_mutex_lock(&lock);HUDState *s=state(v);if(s->arena&&s->arena!=owner)clearRanks(s);s->arena=owner;
 int rank=s->ranks[slot];if(s->actors[slot]&&s->actors[slot]!=(uintptr_t)p){rank=0;s->ranks[slot]=0;}if(rank&&!s->actors[slot])s->actors[slot]=(uintptr_t)p;
 RankPaint j={.p=p,.g=g,.v=v,.slot=slot,.rank=rank,.cap=s->caps[slot],.w=s->w[slot],.h=s->h[slot],.minX=1000000,.minY=1000000,.maxX=-1000000,.maxY=-1000000,.time=(uint64_t)(now()*1000),.native=native};
 pthread_mutex_unlock(&lock);if(!rank||j.cap<=0)return 0;
 pthread_once(&keyOnce,createKey);if(!atomic_load(&keyReady))return 0;
 *(int64_t *)(p+0x70)=j.cap;j.original=save(g);RankPaint *previous=current();pthread_setspecific(paintKey,&j);
 AGWheelGuard(env,ranked,&j,(void *)(base()+0x1300d54));pthread_setspecific(paintKey,previous);restore(env,g,j.original);
 pthread_mutex_lock(&lock);s=&states[v];if(s->ranks[slot]==rank&&s->actors[slot]==(uintptr_t)p){s->w[slot]=j.w;s->h[slot]=j.h;}pthread_mutex_unlock(&lock);return 1;
}
