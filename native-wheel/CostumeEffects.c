/* ShotFx122's costume selection and pixel arithmetic from the supplied APK. */
#include "CostumeEffects.h"
#include "CostumeEffects306.h"
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
typedef struct {uint8_t hero,style;uint16_t head;} Entry;
static struct {Entry *rows;int count;} dynamic[6];
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
int AGCostumeStyleLookup(int hero,int head,int fallback){
 if(hero<0||hero>9||head<0||head>32767)return fallback;
 for(size_t i=0;i<sizeof AGCostumeStyles/sizeof *AGCostumeStyles;i++)
  if(AGCostumeStyles[i].hero==hero&&AGCostumeStyles[i].head==head)return AGCostumeStyles[i].style;
 return fallback;
}
int AGCostumeVariantStyle(int v,int hero,int head,int fallback){
 if(v<0||v>=6)return fallback;int found=0,result=fallback;
 pthread_mutex_lock(&mutex);
 for(int i=0;i<dynamic[v].count;i++)if(dynamic[v].rows[i].hero==hero&&dynamic[v].rows[i].head==head){result=dynamic[v].rows[i].style;found=1;break;}
 pthread_mutex_unlock(&mutex);
 return found?result:AGCostumeStyleLookup(hero,head,fallback);
}
int AGCostumePalette(int hero,int style,uint32_t *primary,uint32_t *secondary){
 for(size_t i=0;i<sizeof AGCostumeStyles/sizeof *AGCostumeStyles;i++)if(AGCostumeStyles[i].hero==hero&&AGCostumeStyles[i].style==style){*primary=AGCostumeStyles[i].primary;*secondary=AGCostumeStyles[i].secondary;return 1;}return 0;
}
uint32_t AGCostumeTint(uint32_t rgba,uint32_t primary,uint32_t secondary){
 int alpha=rgba&255,r=rgba>>24,g=(rgba>>16)&255,b=(rgba>>8)&255;
 int luminance=(r*54+g*183+b*19)>>8;if(!alpha||luminance<35)return rgba;
 int mix=(luminance>190?luminance-190:0)/3;uint32_t out=alpha;
 for(int i=0;i<3;i++){
  int shift=16-i*8,c=(((primary>>shift)&255)*(100-mix)+((secondary>>shift)&255)*mix)/100;
  c=c*(luminance*165/255+90)/255;if(luminance>235)c=(c*7+255)/8;out|=(uint32_t)c<<(24-i*8);
 }return out;
}
/* ShotFx122 also supports server-defined styles: derive its dominant color
   from the first frame, in the same encounter order and 24-level buckets. */
int AGCostumeSheetPalette(int hero,int style,const uint8_t *rgba,int width,int height,uint32_t *a,uint32_t *b){
 if(!rgba||!a||!b||hero<0||hero>9||style<=0||width<1||width>128||height<1)return 0;
 int block=width*(hero==2?2:hero==5?4:1);if(style>=height/block)return 0;
 if(AGCostumePalette(hero,style,a,b))return 1;
 unsigned keys[2048],counts[2048]={0};int n=0,best=-1;
 const uint8_t *p=rgba+(size_t)style*block*width*4;
 for(int i=0;i<width*width;i++,p+=4){
  int max=p[0]>p[1]?p[0]:p[1];if(p[2]>max)max=p[2];
  int min=p[0]<p[1]?p[0]:p[1];if(p[2]<min)min=p[2];
  if(p[3]<160||max<35||min>235)continue;
  unsigned key=(p[0]/24<<8)|(p[1]/24<<4)|(p[2]/24);int j=0;
  while(j<n&&keys[j]!=key)j++;if(j==n){if(n==2048)return 0;keys[n++]=key;}
  counts[j]++;if(best<0||counts[j]>counts[best])best=j;
 }
 if(best<0)return 0;unsigned k=keys[best];*a=*b=((((k>>8)&15)*24+12)<<16)|((((k>>4)&15)*24+12)<<8)|((k&15)*24+12);return 1;
}
int AGCostumeExpandRGBA(int hero,const uint8_t *source,int width,int height,int minStyle,uint8_t **out,int *outHeight){
 if(!out||!outHeight)return 0;*out=NULL;*outHeight=0;
 if(hero<0||hero>9||!source||width<1||width>128||height<1||height>16384||minStyle<0||minStyle>127)return 0;
 int block=width*(hero==2?2:hero==5?4:1),maxStyle=minStyle;if(height<block)return 0;
 uint32_t a,b;if(!AGCostumePalette(hero,minStyle,&a,&b))return 0;
 for(int style=0;style<128;style++)if(AGCostumePalette(hero,style,&a,&b)&&style>maxStyle)maxStyle=style;
 int total=(maxStyle+1)*block;if(total<height)total=height;if(total>16384||(size_t)width*total>2097152)return 0;
 uint8_t *pixels=calloc((size_t)width*total,4);if(!pixels)return 0;memcpy(pixels,source,(size_t)width*height*4);
 for(int style=0;style<=maxStyle;style++){
  if((style+1)*block<=height||!AGCostumePalette(hero,style,&a,&b))continue;
  for(int y=0;y<block;y++)for(int x=0;x<width;x++){
   if(style*block+y<height)continue;const uint8_t *s=source+((size_t)y*width+x)*4;uint8_t *d=pixels+(((size_t)style*block+y)*width+x)*4;
   uint32_t p=AGCostumeTint((uint32_t)s[0]<<24|(uint32_t)s[1]<<16|(uint32_t)s[2]<<8|s[3],a,b);
   d[0]=p>>24;d[1]=p>>16;d[2]=p>>8;d[3]=p;
  }
 }
 *out=pixels;*outHeight=total;return 1;
}
static int advance(size_t *pos,size_t n,size_t length){if(*pos>length||n>length-*pos)return 0;*pos+=n;return 1;}
/* Exactly the optional FX49 cache extension read by CostumeEffects496.load.
   Parsing does not consume or modify the native receive cursor. */
int AGCostumeCatalog(int v,const uint8_t *b,size_t n){
 if(v<0||v>=6||!b||n<1)return 0;size_t p=1;
 int heroes=b[0];if(heroes>10)return 0;
 for(int i=0;i<heroes;i++){
  if(!advance(&p,4,n))return 0;int slots=b[p-1];if(slots>8)return 0;
  for(int s=0;s<slots;s++){if(!advance(&p,2,n))return 0;int kind=b[p-2],count=b[p-1];if(!advance(&p,(size_t)count*(63+(kind==0)),n))return 0;}
 }
 for(int i=0;i<11;i++){if(!advance(&p,2,n))return 0;int len=(b[p-2]<<8)|b[p-1];if(!advance(&p,len,n))return 0;}
 Entry *rows=NULL;int count=0;
 if(p<n){
  if(!advance(&p,7,n)||memcmp(b+p-7,"FX49\1",5))return 0;count=(b[p-2]<<8)|b[p-1];
  if(count>32767||n-p!=(size_t)count*4)return 0;
  if(count&&!(rows=calloc(count,sizeof *rows)))return 0;
  for(int i=0;i<count;i++,p+=4){int hero=b[p],head=(b[p+1]<<8)|b[p+2],style=b[p+3];if(hero>9||head>32767||style>127){free(rows);return 0;}rows[i]=(Entry){hero,style,head};}
 }
 pthread_mutex_lock(&mutex);Entry *old=dynamic[v].rows;dynamic[v].rows=rows;dynamic[v].count=count;pthread_mutex_unlock(&mutex);free(old);return 1;
}
void AGCostumeObserve(void *opaque,int v){
 if(!opaque||v<0||v>=6)return;uint8_t *m=opaque;if(*(int8_t *)(m+0x30)!=90)return;
 uint8_t *in=*(void **)(m+0x20),*a=in?*(void **)(in+0x10):NULL;if(!a)return;
 int cap=*(int *)(a+0x10),end=*(int *)(in+0x18),pos=*(int *)(in+0x20);
 if(pos<0||end<pos||end>cap||end-pos<6||end-pos>2000000)return;uint8_t *b=a+0x14+pos;
 uint32_t n=(uint32_t)b[2]<<24|(uint32_t)b[3]<<16|(uint32_t)b[4]<<8|b[5];
 if(b[0]==4&&n==(uint32_t)(end-pos-6))AGCostumeCatalog(v,b+6,n);
}
