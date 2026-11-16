#import <UIKit/UIKit.h>
#include <stdlib.h>
#include <pthread.h>
#include <mach-o/dyld.h>
#include "HUD.h"
#include "ProfileIcons.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {void *source,*result;int rank,w,h;uint64_t touched;size_t pixels;} Cached;
static Cached cache[16];static uint64_t clockTick;static size_t cachedPixels;static pthread_mutex_t imageLock=PTHREAD_MUTEX_INITIALIZER;
typedef struct {const uint8_t *bytes;int length;void *result;} LoadImage;
static int loadImage(void *env,void *opaque){
 LoadImage *j=opaque;void **jni=*(void ***)env;
 void *bytes=((void *(*)(void *,int))jni[176])(env,j->length);if(!bytes)return 0;
 ((void (*)(void *,void *,int,int,const void *))jni[208])(env,bytes,0,j->length,j->bytes);
 void *image=((void *(*)(void *,void *,int,int))((uintptr_t)_dyld_get_image_header(0)+0xc46e04))(env,bytes,0,j->length);
 if(image)j->result=((void *(*)(void *,void *))jni[21])(env,image);
 ((void (*)(void *,void *))jni[23])(env,bytes);return j->result!=NULL;
}
static void discard(void *env,Cached *c){
 if(!c->result)return;void **jni=*(void ***)env;
 ((void (*)(void *,void *))jni[22])(env,c->result);((void (*)(void *,void *))jni[22])(env,c->source);
 cachedPixels-=c->pixels;*c=(Cached){0};
}
/* Render thread only. Source and result are separately rooted; never tint a
   shared native atlas in place. Failed conversions remain retryable. */
static void *rankImage(void *env,void *source,int rank,int width,int height){
 if(!env||!source||rank<1||rank>3)return NULL;
 for(int i=0;i<16;i++)if(cache[i].source==source&&cache[i].rank==rank&&cache[i].w==width&&cache[i].h==height){cache[i].touched=++clockTick;return cache[i].result;}
 int fire=width>0,sw=*(int *)((uint8_t *)source+0x20),sh=*(int *)((uint8_t *)source+0x24);
 int w=fire?width:sw,h=fire?height*4:sh;
 if(sw<1||sh<1||w<1||h<1||sw>1024||sh>1024||(size_t)sw*sh>1000000||w>1024||h>1024||(size_t)w*h>1000000)return NULL;
 if(fire&&(sw<41||sh<188||width>256||height<1||height>256))return NULL;
 AGProfileIcon image={0};if(!AGNativeImageRGBA(env,source,0,0,fire?41:sw,fire?188:sh,&image))return NULL;
 uint8_t *pixels=malloc((size_t)w*h*4);if(!pixels){free(image.rgba);return NULL;}
 for(int y=0;y<h;y++)for(int x=0;x<w;x++){
  int sx=fire?x*41/w:x,sy=fire?(y/height)*47+(y%height)*47/height:y;
  const uint8_t *p=image.rgba+(sy*(fire?41:sw)+sx)*4;
  uint32_t c=AGRankPixel((uint32_t)p[3]<<24|(uint32_t)p[0]<<16|(uint32_t)p[1]<<8|p[2],rank,fire);
  uint8_t *d=pixels+(y*w+x)*4;d[0]=c>>16;d[1]=c>>8;d[2]=c;d[3]=c>>24;
 }
 free(image.rgba);
 CGColorSpaceRef space=CGColorSpaceCreateDeviceRGB();CGDataProviderRef provider=CGDataProviderCreateWithData(NULL,pixels,(size_t)w*h*4,NULL);
 CGImageRef cg=CGImageCreate(w,h,8,32,w*4,space,kCGImageAlphaLast|kCGBitmapByteOrderDefault,provider,NULL,NO,kCGRenderingIntentDefault);
 __attribute__((objc_precise_lifetime)) NSData *png=cg?UIImagePNGRepresentation([UIImage imageWithCGImage:cg]):nil;
 if(cg)CGImageRelease(cg);CGDataProviderRelease(provider);CGColorSpaceRelease(space);free(pixels);
 if(!png.length||png.length>2000000)return NULL;
 LoadImage job={png.bytes,(int)png.length,NULL};
 if(AGWheelGuard(env,loadImage,&job,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54))<=0||!job.result)return NULL;
 void **jni=*(void ***)env;void *root=((void *(*)(void *,void *))jni[21])(env,source);
 if(!root){((void (*)(void *,void *))jni[22])(env,job.result);return NULL;}
 size_t size=(size_t)w*h;
 while(cachedPixels+size>1000000){int oldest=-1;for(int i=0;i<16;i++)if(cache[i].result&&(oldest<0||cache[i].touched<cache[oldest].touched))oldest=i;if(oldest<0)break;discard(env,&cache[oldest]);}
 int slot=0;for(int i=0;i<16;i++){if(!cache[i].result){slot=i;break;}if(cache[i].touched<cache[slot].touched)slot=i;}
 discard(env,&cache[slot]);cache[slot]=(Cached){root,job.result,rank,width,height,++clockTick,size};cachedPixels+=size;return job.result;
}
void *AGRankImage(void *env,void *source,int rank,int width,int height){
 if(pthread_mutex_trylock(&imageLock))return NULL;
 void *result=rankImage(env,source,rank,width,height);pthread_mutex_unlock(&imageLock);return result;
}
