#import <UIKit/UIKit.h>
#include <mach-o/dyld.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "CostumeEffects.h"
#include "ProfileIcons.h"
#include "TurnMap.h"
#include "NotesMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
extern int AGCostumeVariantStyle(int,int,int,int);
extern int AGCostumePalette(int,int,uint32_t *,uint32_t *);
static const uintptr_t catalogs[6]={0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0};
static pthread_mutex_t fxMutex=PTHREAD_MUTEX_INITIALIZER;
static struct {uintptr_t source,prepared;int failed;double attempted;} sheets[6][10];
static struct {uintptr_t actor,outfit;int original,applied,head;} actors[6][24];
static uintptr_t fxBase(void){return (uintptr_t)_dyld_get_image_header(0);}
static int guarded(void *env,int (*fn)(void *,void *),void *job){return AGWheelGuard(env,fn,job,(void *)(fxBase()+0x1300d54));}
static uint8_t *objectAt(uint8_t *array,int index){return array&&index>=0&&index<*(int *)(array+0x10)?*(void **)(array+0x18+index*8):NULL;}
typedef struct {int v,hero,style,head,slot,ready,original;uint8_t *actor,*array,*source;void *arrayRoot,*imageRoot,*newRoot;const uint8_t *png;int pngLength;} FXJob;
static int info(void *env,void *opaque){
 FXJob *j=opaque;uint8_t *p=j->actor,*outfit=p?*(void **)(p+0x60):NULL,*parts=outfit?*(void **)(outfit+0x10):NULL,*head=objectAt(parts,1);
 if(!p)return 0;j->original=*(int *)(p+0x104);if(!head)return 0;j->hero=(int8_t)head[0xc3];if(j->hero<0||j->hero>9)j->hero=p[0x16c];
 if(j->hero>9)return 0;int64_t id=*(int64_t *)(head+0x80);if(id<0||id>32767)return 0;j->head=(int)id;
 j->original=*(int *)(p+0x104);j->style=AGCostumeVariantStyle(j->v,j->hero,j->head,-1);
 uint8_t *c=*(void **)(fxBase()+catalogs[j->v]);j->array=c?*(void **)(c+0xa8):NULL;j->source=objectAt(j->array,j->hero);
 if(!j->source||j->style<0)return 0;
 int w=*(int *)(j->source+0x20),h=*(int *)(j->source+0x24),frames=j->hero==2?2:j->hero==5?4:1;
 j->ready=w>0&&w<=128&&h>=(j->style+1)*w*frames;return 1;
}
__attribute__((noinline)) static void logFX(int v,const FXJob *j,int expanded){
 static NSMutableArray *history;static dispatch_queue_t queue;static dispatch_once_t once;
 dispatch_once(&once,^{queue=dispatch_queue_create("army2.costume.numeric",DISPATCH_QUEUE_SERIAL);history=[NSMutableArray array];});
 NSDictionary *row=@{@"pb":@(v+1),@"hero":@(j->hero),@"head":@(j->head),@"style":@(j->style),@"native_style":@(j->original),@"expanded_sheet":@(expanded)};
 dispatch_async(queue,^{
  [history addObject:row];while(history.count>64)[history removeObjectAtIndex:0];
  NSData *data=[NSJSONSerialization dataWithJSONObject:@{@"build":@306,@"events":[history copy]} options:0 error:nil];
  NSString *path=[NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject stringByAppendingPathComponent:@"Costume306-diagnostic.json"];
  [data writeToFile:path atomically:YES];
 });
}
static int rootImages(void *env,void *opaque){
 FXJob *j=opaque;void **jni=*(void ***)env;
 j->arrayRoot=((void *(*)(void *,void *))jni[21])(env,j->array);
 j->imageRoot=((void *(*)(void *,void *))jni[21])(env,j->source);return j->arrayRoot&&j->imageRoot;
}
static int installImage(void *env,void *opaque){
 FXJob *j=opaque;void **jni=*(void ***)env;uintptr_t b=fxBase();uint8_t *c=*(void **)(b+catalogs[j->v]);
 if(!c||*(void **)(c+0xa8)!=j->array||objectAt(j->array,j->hero)!=j->source)return 0;
 void *bytes=((void *(*)(void *,int))jni[176])(env,j->pngLength);if(!bytes)return 0;
 ((void (*)(void *,void *,int,int,const uint8_t *))jni[208])(env,bytes,0,j->pngLength,j->png);
 void *image=((void *(*)(void *,void *,int,int))(b+0xc46e04))(env,bytes,0,j->pngLength);
 if(image)j->newRoot=((void *(*)(void *,void *))jni[21])(env,image);
 ((void (*)(void *,void *))jni[23])(env,bytes);
 if(!j->newRoot)return 0;
 ((void (*)(void *,void *,int,void *))jni[174])(env,j->array,j->hero,j->newRoot);return 1;
}
/* Preserve real rows. Missing costume rows use ShotFx122's exact palette and
   luminance arithmetic; physics, trajectory and damage stay in native code. */
static int prepare(void *env,FXJob *j){
 __attribute__((objc_precise_lifetime)) NSData *png=nil;uint32_t tintA,tintB;
 int v=j->v,h=j->hero;if(!AGCostumePalette(h,j->style,&tintA,&tintB))return 0;
 struct timespec now;clock_gettime(CLOCK_MONOTONIC,&now);double time=now.tv_sec+now.tv_nsec/1e9;
 if(sheets[v][h].failed&&(uintptr_t)j->source==sheets[v][h].source&&time<sheets[v][h].attempted+2)return 0;
 sheets[v][h].source=(uintptr_t)j->source;sheets[v][h].failed=1;sheets[v][h].attempted=time;
 if(guarded(env,rootImages,j)<=0)goto failed;
 int w=*(int *)(j->source+0x20),oldH=*(int *)(j->source+0x24);uint8_t *source=NULL,*pixels=NULL;int height=0;
 if(w<1||w>128||oldH<1||oldH>16384)goto failed;
 source=malloc((size_t)w*oldH*4);if(!source)goto failed;
 int copied=1;
 for(int y=0;y<oldH;y+=1024){AGProfileIcon region;int n=oldH-y;if(n>1024)n=1024;
  if(!AGNativeImageRGBA(env,j->source,0,y,w,n,&region)){copied=0;break;}memcpy(source+(size_t)y*w*4,region.rgba,(size_t)n*w*4);free(region.rgba);
 }
 if(!copied||!AGCostumeExpandRGBA(h,source,w,oldH,j->style,&pixels,&height)){free(source);goto failed;}free(source);
 CGColorSpaceRef color=CGColorSpaceCreateDeviceRGB();CGDataProviderRef provider=CGDataProviderCreateWithData(NULL,pixels,(size_t)w*height*4,NULL);
 CGImageRef image=CGImageCreate(w,height,8,32,w*4,color,kCGImageAlphaLast|kCGBitmapByteOrderDefault,provider,NULL,NO,kCGRenderingIntentDefault);
 png=image?UIImagePNGRepresentation([UIImage imageWithCGImage:image]):nil;
 if(image)CGImageRelease(image);CGDataProviderRelease(provider);CGColorSpaceRelease(color);free(pixels);
 if(png.length&&png.length<2000000){j->png=png.bytes;j->pngLength=(int)png.length;
  if(guarded(env,installImage,j)>0){sheets[v][h].prepared=(uintptr_t)j->newRoot;sheets[v][h].failed=0;j->ready=1;}
 }
failed:;
 void **jni=*(void ***)env;
 void *roots[3]={j->arrayRoot,j->imageRoot,j->newRoot};for(int i=0;i<3;i++)if(roots[i])((void (*)(void *,void *))jni[22])(env,roots[i]);
 return j->ready;
}
static int apply(void *env,void *opaque){
 FXJob *j=opaque;int v=j->v,slot=j->slot;uint8_t *p=j->actor;uintptr_t outfit=(uintptr_t)*(void **)(p+0x60);
 if(actors[v][slot].actor!=(uintptr_t)p||actors[v][slot].outfit!=outfit){actors[v][slot].actor=(uintptr_t)p;actors[v][slot].outfit=outfit;actors[v][slot].original=j->original;actors[v][slot].applied=-1;actors[v][slot].head=-1;}
 if(j->original!=actors[v][slot].applied)actors[v][slot].original=j->original;
 int style=j->ready?j->style:actors[v][slot].original;
 *(int *)(p+0x104)=style;
 int changed=actors[v][slot].head!=j->head||actors[v][slot].applied!=style;
 actors[v][slot].applied=style;actors[v][slot].head=j->head;
 return changed;
}
static void updateActor(void *env,FXJob *j,int canPrepare){
 int found=guarded(env,info,j)>0;
 if(!found&&(actors[j->v][j->slot].actor!=(uintptr_t)j->actor||actors[j->v][j->slot].applied<0))return;
 if(found&&!j->ready&&canPrepare)prepare(env,j);
 if(!found){j->ready=0;j->style=-1;}
 if(guarded(env,apply,j)>0)logFX(j->v,j,found&&j->ready&&sheets[j->v][j->hero].prepared!=0);
}
void AGCostumePaint(void *env,uint8_t *actor,int v){
 if(!env||!actor||v<0||v>=6||actor[0x16c]>9||pthread_mutex_trylock(&fxMutex))return;
 /* Native roster slot is +0x16b; use it only as a bounded local cache key. */
 int slot=actor[0x16b];if(slot<24){FXJob j={.v=v,.actor=actor,.slot=slot,.hero=-1,.head=-1,.style=-1};updateActor(env,&j,1);}pthread_mutex_unlock(&fxMutex);
}
typedef struct {int v;uint8_t *array;} Roster;
static int roster(void *env,void *opaque){
 Roster *j=opaque;uintptr_t b=fxBase();uint8_t *canvas=*(void **)(b+AGNotesMaps[j->v].canvas),*arena=*(void **)(b+AGTurnMaps[j->v].arena_class),*g=*(void **)(b+AGTurnMaps[j->v].array_class);
 if(!canvas||!arena||!g||!*(void **)(arena+0xe8)||*(void **)(canvas+0xb8)!=*(void **)(arena+0xe8))return 0;
 j->array=*(void **)(g+0xa0);return j->array&&*(int *)(j->array+0x10)>0&&*(int *)(j->array+0x10)<=24;
}
void AGCostumeTick(void *env,int v){
 if(!env||v<0||v>=6||pthread_mutex_trylock(&fxMutex))return;Roster r={.v=v};
 if(guarded(env,roster,&r)>0){int n=*(int *)(r.array+0x10);for(int i=0;i<n;i++){uint8_t *p=objectAt(r.array,i);if(!p||p[0x16c]>9)continue;FXJob j={.v=v,.actor=p,.slot=i,.hero=-1,.head=-1,.style=-1};updateActor(env,&j,0);}}
 pthread_mutex_unlock(&fxMutex);
}
