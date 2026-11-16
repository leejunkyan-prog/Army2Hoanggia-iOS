#include "HUD.h"
#include <string.h>
static uint32_t be32(const uint8_t *p){return (uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3];}
/* DataOutputStream.writeUTF uses modified UTF-8 and UTF-16 code units. */
static int utf(const uint8_t *p,size_t n,uint16_t *out,size_t *length){
 size_t i=0,k=0;
 while(i<n){unsigned a=p[i++],c;
  if(a&&a<128)c=a;
  else if((a&224)==192){if(i>=n||(p[i]&192)!=128)return 0;c=(a&31)<<6|(p[i++]&63);if(c<128&&c!=0)return 0;}
  else if((a&240)==224){if(n-i<2||(p[i]&192)!=128||(p[i+1]&192)!=128)return 0;c=(a&15)<<12|(p[i]&63)<<6|(p[i+1]&63);i+=2;if(c<2048)return 0;}
  else return 0;
  if(k>=AGHUDTextLimit)return 0;out[k++]=(uint16_t)c;
 }
 out[k]=0;*length=k;return 1;
}
int AGHUDParse(int command,const uint8_t *p,size_t n,AGHUDPacket *out){
 if(!p||!out)return 0;
 size_t start=0,bytes=0;
 if(command==-116){if(n<10)return 0;bytes=(p[0]<<8)|p[1];start=2;if(bytes+10!=n)return 0;}
 else if(command==-121){
  if(n==1&&p[0]==4){*out=(AGHUDPacket){.kind=4};return 1;}
  if(n<9||p[0]!=2||p[1]>=AGHUDSlots||p[2]<1||p[2]>3)return 0;
  bytes=(p[3]<<8)|p[4];start=5;if(bytes+9!=n)return 0;
 }else return 0;
 if(!utf(p+start,bytes,out->text,&out->length))return 0;
 if(command==-116){
  int32_t seconds=(int32_t)be32(p+start+bytes+4);
  out->kind=1;out->seconds=seconds<0?0:seconds; /* APK ignores the wire speed; one pixel per canvas tick. */
 }else{
  uint32_t cap=be32(p+start+bytes);if(!cap||cap>INT32_MAX)return 0;
  out->kind=2;out->slot=p[1];out->rank=p[2];out->maximum=(int)cap;
 }
 return 1;
}
int AGRankColor(int r){return r==1?2476799:r==2?12875519:r==3?5369233:0;}
uint32_t AGRankPixel(uint32_t p,int r,int fire){
 if(!(p>>24)||r<1||r>3)return p;
 int a=(p>>16)&255,b=(p>>8)&255,c=p&255;
 if(!fire&&a>235&&b>235&&c>235)return p;
 int lum=(a*3+b*6+c)/10,level=fire?lum+20:lum*190/255+65;
 if(level>255)level=255;
 unsigned tint=AGRankColor(r);int rr=((tint>>16)&255)*level/255,gg=((tint>>8)&255)*level/255,bb=(tint&255)*level/255;
 if(fire&&lum>185){int glow=(lum-185)*3;rr+=glow;gg+=glow;bb+=glow;if(rr>255)rr=255;if(gg>255)gg=255;if(bb>255)bb=255;}
 return (p&0xff000000U)|(uint32_t)rr<<16|(uint32_t)gg<<8|(uint32_t)bb;
}
