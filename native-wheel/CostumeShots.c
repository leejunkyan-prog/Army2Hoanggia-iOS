/* Bind APK ShotFx122's separate POW/egg images after native construction.
   Only image references change. The original projectile state remains native. */
#include <stdint.h>
#include <string.h>
#include <pthread.h>
#include <mach-o/dyld.h>
#include "CostumeEffects.h"
#include "TurnMap.h"
#include "NotesMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static const uintptr_t catalogs[6]={0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0};
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
typedef struct {void *root,*helper,*image;int seen;} Shot;
static Shot shots[6][96];
typedef struct {int v;} Job;
static uint8_t *at(uint8_t *a,int i){return a&&i>=0&&i<*(int *)(a+0x10)?*(void **)(a+0x18+i*8):NULL;}
static void release(void *env,Shot *s){if(s->root)((void (*)(void *,void *))(*(void ***)env)[22])(env,s->root);memset(s,0,sizeof *s);}
static void replace(void *env,uint8_t *owner,int offset,void *sheet,int hero,int style,int frames){
 void *source=*(void **)(owner+offset);if(!source)return;
 void *image=AGCostumeImage(env,source,sheet,hero,style,frames);if(image)*(void **)(owner+offset)=image;
}
static int render(void *env,void *opaque){
 int v=((Job *)opaque)->v;uintptr_t base=(uintptr_t)_dyld_get_image_header(0);void **jni=*(void ***)env;
 uint8_t *canvas=*(void **)(base+AGNotesMaps[v].canvas),*arena=*(void **)(base+AGTurnMaps[v].arena_class);
 uint8_t *manager=NULL,*array=NULL;int n=0;
 if(canvas&&arena&&*(void **)(arena+0xe8)&&*(void **)(canvas+0xb8)==*(void **)(arena+0xe8)){
  manager=*(void **)(arena+0xe0);uint8_t *vector=manager?*(void **)(manager+0x30):NULL;
  array=vector?*(void **)(vector+0x18):NULL;n=vector?*(int *)(vector+0x24):0;
  if(!array||n<0||n>96||n>*(int *)(array+0x10))n=0;
 }
 for(int s=0;s<96;s++)shots[v][s].seen=0;
 for(int i=0;i<n;i++){
  uint8_t *p=at(array,i);if(!p)continue;int type=p[0xcf],phase=(int8_t)manager[0x64],hero=-1,frames=0;
  if(type==0&&phase==1)hero=0;
  else if(type==9&&phase==1)hero=3;
  else if(type==11&&phase==1)hero=5;
  else if(type==12){hero=5;frames=4;}
  else if(type==19&&phase==1)hero=6;
  else if(type==20)hero=6;
  else if(type==21&&phase==1)hero=7;
  if(hero<0)continue;
  Shot *state=NULL;for(int s=0;s<96;s++)if(shots[v][s].root==p){state=&shots[v][s];break;}
  if(!state)for(int s=0;s<96;s++)if(!shots[v][s].root){state=&shots[v][s];state->root=((void *(*)(void *,void *))jni[21])(env,p);break;}
  if(!state||!state->root)continue;state->seen=1;
  void *helper=*(void **)(p+0x38),*direct=*(void **)(p+0x28);
  if(state->helper==helper&&state->image==direct)continue;
  /* Native Granos POW resets +0x4c; its original style survives in manager+58.
     Type12 is the secondary four-frame Granos projectile, also created at0. */
  int style=type==11||type==12?*(int *)(manager+0x58):*(int *)(p+0x4c);
  uint8_t *catalog=*(void **)(base+catalogs[v]),*sheets=catalog?*(void **)(catalog+0xa8):NULL;void *sheet=at(sheets,hero);
  if(style<=0||style>127||!sheet)continue;
  if(helper){
   replace(env,helper,0x18,sheet,hero,style,frames);
   uint8_t *rotations=*(void **)((uint8_t *)helper+0x10);int count=rotations?*(int *)(rotations+0x10):0;
   if(count>0&&count<=360)for(int r=0;r<count;r++){
    void *source=at(rotations,r);if(!source)continue;void *image=AGCostumeImage(env,source,sheet,hero,style,0);
    if(image)((void (*)(void *,void *,int,void *))jni[174])(env,rotations,r,image);
   }
  }else replace(env,p,0x28,sheet,hero,style,0);
  state->helper=*(void **)(p+0x38);state->image=*(void **)(p+0x28);
 }
 for(int s=0;s<96;s++)if(shots[v][s].root&&!shots[v][s].seen)release(env,&shots[v][s]);return 1;
}
void AGCostumeRender(void *env,int v){
 if(!env||v<0||v>=6||pthread_mutex_trylock(&mutex))return;Job j={v};
 AGWheelGuard(env,render,&j,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54));pthread_mutex_unlock(&mutex);
}
