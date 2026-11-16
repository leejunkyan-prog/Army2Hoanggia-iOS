#import <UIKit/UIKit.h>
#include <mach-o/dyld.h>
#include <stdlib.h>
#include <string.h>
#include "CostumeEffects.h"
#include "ProfileIcons.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
typedef struct {void *source,*sheet,*result;int hero,style,frames;} ImageJob;
static ImageJob cache[32];static unsigned cursor;
static int make(void *env,void *opaque){
 ImageJob *j=opaque;void **jni=*(void ***)env;void *bytes=NULL;
 bytes=((void *(*)(void *,int))jni[176])(env,j->frames);if(!bytes)return 0;
 ((void (*)(void *,void *,int,int,const void *))jni[208])(env,bytes,0,j->frames,j->source);
 void *image=((void *(*)(void *,void *,int,int))((uintptr_t)_dyld_get_image_header(0)+0xc46e04))(env,bytes,0,j->frames);
 if(image)j->result=((void *(*)(void *,void *))jni[21])(env,image);
 ((void (*)(void *,void *))jni[23])(env,bytes);return j->result!=NULL;
}
void *AGCostumeImage(void *env,void *source,void *sheet,int hero,int style,int frames){
 if(!env||!source||!sheet||hero<0||hero>9||style<=0||style>127||(frames!=0&&frames!=1&&frames!=4))return NULL;
 for(int i=0;i<32;i++)if(cache[i].source==source&&cache[i].sheet==sheet&&cache[i].hero==hero&&cache[i].style==style&&cache[i].frames==frames)return cache[i].result;
 uint8_t *s=source,*sh=sheet;int w=*(int *)(s+0x20),h=*(int *)(s+0x24),sw=*(int *)(sh+0x20),height=*(int *)(sh+0x24),y=0;
 if(w<=0||w>128||h<=0||h>16384||sw<=0||sw>128||height<=0||height>16384)return NULL;
 uint32_t a=0,b=0;AGProfileIcon pixels={0},palette={0};
 if(frames){int count=h/(w*frames);if(count<=0||(frames==1&&style>=count))return NULL;int index=style<count?style:count-1;y=index*w*frames;h=w*frames;}
 else{
  if(style>=height/(sw*(hero==2?2:hero==5?4:1)))return NULL;
  extern int AGCostumePalette(int,int,uint32_t *,uint32_t *);
  if(!AGCostumePalette(hero,style,&a,&b)){
   int block=sw*(hero==2?2:hero==5?4:1);
   if(!AGNativeImageRGBA(env,sheet,0,style*block,sw,sw,&palette))return NULL;
   /* Place the extracted frame at its original style offset for the same C parser. */
   size_t length=(size_t)sw*block*(style+1)*4;uint8_t *whole=calloc(length,1);
   if(whole)memcpy(whole+(size_t)style*block*sw*4,palette.rgba,(size_t)sw*sw*4);
   int ok=whole&&AGCostumeSheetPalette(hero,style,whole,sw,block*(style+1),&a,&b);free(whole);free(palette.rgba);if(!ok)return NULL;
  }
 }
 if(h>1024||!AGNativeImageRGBA(env,source,0,y,w,h,&pixels))return NULL;
 if(!frames)for(int i=0;i<w*h;i++){uint8_t *p=pixels.rgba+i*4;uint32_t c=AGCostumeTint((uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3],a,b);p[0]=c>>24;p[1]=c>>16;p[2]=c>>8;p[3]=c;}
 CGColorSpaceRef color=CGColorSpaceCreateDeviceRGB();CGDataProviderRef provider=CGDataProviderCreateWithData(NULL,pixels.rgba,(size_t)w*h*4,NULL);
 CGImageRef cg=CGImageCreate(w,h,8,32,w*4,color,kCGImageAlphaLast|kCGBitmapByteOrderDefault,provider,NULL,NO,kCGRenderingIntentDefault);
 __attribute__((objc_precise_lifetime)) NSData *png=cg?UIImagePNGRepresentation([UIImage imageWithCGImage:cg]):nil;
 if(cg)CGImageRelease(cg);CGDataProviderRelease(provider);CGColorSpaceRelease(color);free(pixels.rgba);if(!png.length||png.length>2000000)return NULL;
 ImageJob job={.source=(void *)png.bytes,.frames=(int)png.length};
 if(AGWheelGuard(env,make,&job,(void *)((uintptr_t)_dyld_get_image_header(0)+0x1300d54))<=0||!job.result)return NULL;
 ImageJob *entry=&cache[cursor++%32];void **jni=*(void ***)env;
 if(entry->result){void *old[3]={entry->source,entry->sheet,entry->result};for(int i=0;i<3;i++)if(old[i])((void (*)(void *,void *))jni[22])(env,old[i]);}
 entry->source=((void *(*)(void *,void *))jni[21])(env,source);entry->sheet=((void *(*)(void *,void *))jni[21])(env,sheet);
 entry->result=job.result;entry->hero=hero;entry->style=style;entry->frames=frames;return job.result;
}

