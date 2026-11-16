/* Included by Notes77.m. Use the original game Env and native guard. */
#include "ProfileIcons.h"
static const uintptr_t NProfileCatalogs[6]={0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0};
static const uintptr_t NProfileConsumables[6]={0x2098970,0x20c7200,0x20f4ef0,0x2122be0,0x21508d0,0x217e5c0};
static const uintptr_t NProfileActors[6]={0x2091b80,0x20c0670,0x20ee360,0x211c050,0x2149d40,0x2177a30};
static uint8_t *NProfileVector(uint8_t *v,int *count){
 *count=0;if(!v)return NULL;uint8_t *a=*(void **)(v+0x18);int n=*(int *)(v+0x24);
 if(!a||n<0||n>4096||n>*(int *)(a+0x10))return NULL;*count=n;return a+0x18;
}
static uint8_t *NProfileTemplate(int v,int h,int s,int id){
 uint8_t *c=*(void **)(NBase()+NProfileCatalogs[v]);int nh=0;
 uint8_t **heroes=c?(void *)NProfileVector(*(void **)(c+0xb0),&nh):NULL;
 for(int i=0;heroes&&i<nh;i++){
  uint8_t *hero=heroes[i];if(!hero||(int8_t)hero[0x1a]!=h)continue;
  int ns=0;uint8_t **slots=(void *)NProfileVector(*(void **)(hero+0x10),&ns);
  for(int j=0;slots&&j<ns;j++){
   uint8_t *slot=slots[j];if(!slot||(int8_t)slot[0x18]!=s)continue;
   int ni=0;uint8_t **items=(void *)NProfileVector(*(void **)(slot+0x10),&ni);
   for(int k=0;items&&k<ni;k++)if(items[k]&&*(int64_t *)(items[k]+0x80)==id)return items[k];
  }
 }
 return NULL;
}
typedef struct {uint8_t *image;int x,y,w,h,frame;AGProfileIcon *out;void *root,*pixmap;int dispose;} NImageRegion;
__attribute__((noinline,optnone)) static int NCopyImageRegion(void *env,void *opaque){
 NImageRegion *j=opaque;AGProfileIcon *o=j->out;void **jni=*(void ***)env;uintptr_t b=NBase();
 if(!j->image)return 0;
 j->root=((void *(*)(void *,void *))jni[21])(env,j->image);if(!j->root)return 0;
 int iw=*(int *)(j->image+0x20),ih=*(int *)(j->image+0x24);
 if(iw<1||ih<1||iw>2048||ih>8192)return 0;
 int w=j->w?j->w:iw,h=j->h?j->h:ih,sx=j->x,sy=j->y,pw=iw,ph=ih;
 if(w<1||h<1||w>1024||h>1024||(size_t)w*h>1048576)return 0;
 uint8_t *array=*(void **)(j->image+0x10),*direct=NULL;const uint32_t *words=NULL;
 if(array){
  int count=*(int *)(array+0x10);if(count<iw*ih||count%iw)return 0;
  ph=count/iw;words=(void *)(array+0x14);
 }else{
  void *texture=*(void **)(j->image+0x18);if(!texture)return 0;
  void *data=((void *(*)(void *,void *))(b+0x1b4ba8))(env,texture);if(!data)return 0;
  if(!((int (*)(void *,void *))(b+0x39dc58))(env,data))((void (*)(void *,void *))(b+0x39dcac))(env,data);
  j->dispose=((int (*)(void *,void *))(b+0x39dd54))(env,data);
  void *pm=((void *(*)(void *,void *))(b+0x39dd00))(env,data);if(!pm)return 0;
  j->pixmap=((void *(*)(void *,void *))jni[21])(env,pm);if(!j->pixmap)return 0;
  pw=((int (*)(void *,void *))(b+0x398e0c))(env,pm);ph=((int (*)(void *,void *))(b+0x398e30))(env,pm);
  if(pw<1||ph<1||pw>8192||ph>65536||(size_t)pw*ph>16777216)return 0;
  void *buffer=((void *(*)(void *,void *))(b+0x398fe8))(env,pm);
  if(buffer&&jni[230]&&jni[231]){
   int64_t cap=((int64_t (*)(void *,void *))jni[231])(env,buffer);
   if(cap==(int64_t)pw*ph*4)direct=((void *(*)(void *,void *))jni[230])(env,buffer);
  }
 }
 /* Cropped native textures can retain the WHOLE source PNG in TextureData.
    Image.l(0,0) then returns the first icon for every item. Use its own row. */
 if(j->frame>=0&&ph>ih){
  if(pw!=iw||ph%ih||j->frame>=ph/ih){o->status=7;return 0;}
  sy+=j->frame*ih;
 }
 if(sx<0||sy<0||sx+w>pw||sy+h>ph){o->status=7;return 0;}
 o->rgba=malloc((size_t)w*h*4);if(!o->rgba)return 0;
 for(int y=0;y<h;y++)for(int x=0;x<w;x++){
  uint8_t *dst=o->rgba+((size_t)y*w+x)*4;
  if(direct)memcpy(dst,direct+((size_t)(sy+y)*pw+sx+x)*4,4);
  else{
   uint32_t p=words?words[(size_t)(sy+y)*pw+sx+x]:((uint32_t (*)(void *,void *,int,int))(b+0x1db1f8))(env,j->pixmap,sx+x,sy+y);
   dst[0]=p>>24;dst[1]=p>>16;dst[2]=p>>8;dst[3]=p;
  }
 }
 o->width=w;o->height=h;o->status=0;return 1;
}
static int NDisposePixmap(void *env,void *opaque){((void (*)(void *,void *))(NBase()+0x398e54))(env,opaque);return 1;}
static int NReadImageRegion(void *env,uint8_t *image,int x,int y,int w,int h,int frame,AGProfileIcon *out){
 NImageRegion j={.image=image,.x=x,.y=y,.w=w,.h=h,.frame=frame,.out=out};
 int result=NRun(env,NCopyImageRegion,&j);void **jni=*(void ***)env;
 if(j.pixmap){if(j.dispose)NRun(env,NDisposePixmap,j.pixmap);((void (*)(void *,void *))jni[22])(env,j.pixmap);}
 if(j.root)((void (*)(void *,void *))jni[22])(env,j.root);
 if(result<=0){free(out->rgba);out->rgba=NULL;if(result<0)out->status=6;return 0;}return 1;
}
typedef struct {int variant,hero,slot,id;AGProfileIcon *out;uint8_t *image;} NProfileIconJob;
static int NFindProfileIcon(void *env,void *opaque){
 NProfileIconJob *j=opaque;uintptr_t b=NBase();AGProfileIcon *out=j->out;
 if(j->slot<5){
  uint8_t *item=NProfileTemplate(j->variant,j->hero,j->slot,j->id);if(!item){out->status=1;return 0;}
  int64_t icon=*(int64_t *)(item+0x88);if(icon<0||icon>32767){out->status=2;return 0;}out->iconID=icon;
  void *cache=((void *(*)(void *))(b+0xc46b40))(env);
  void *key=((void *(*)(void *,int))(b+0xab216c))(env,(int)icon);
  if(cache&&key)j->image=((void *(*)(void *,void *,void *))(b+0xbc88a0))(env,cache,key);
 }else{
  uint8_t *c=*(void **)(b+NProfileConsumables[j->variant]);int n=0;
  uint8_t **rows=c?(void *)NProfileVector(*(void **)(c+0xa0),&n):NULL;
  for(int i=0;rows&&i<n;i++)if(rows[i]&&*(int64_t *)(rows[i]+0x18)==j->id){j->image=*(void **)(rows[i]+0x10);break;}
 }
 if(!j->image){out->status=3;return 0;}
 if(*(int *)(j->image+0x20)>128||*(int *)(j->image+0x24)>128){out->status=4;return 0;}return 1;
}
int AGProfileIconRead(void *env,int variant,int hero,int slot,int id,AGProfileIcon *out){
 if(!out)return 0;*out=(AGProfileIcon){.status=6,.iconID=-1};
 if(!env||variant<0||variant>=6||hero<0||hero>9||slot<0||slot>5||id<0||id>32767)return 0;
 NProfileIconJob j={.variant=variant,.hero=hero,.slot=slot,.id=id,.out=out};
 if(NRun(env,NFindProfileIcon,&j)<=0)return 0;
 return NReadImageRegion(env,j.image,0,0,0,0,out->iconID,out);
}
typedef struct {int variant,hero,parts[5];uint8_t *body,*atlas;int rect[5][6];} NAvatarJob;
static uint8_t *NArrayObject(uint8_t *a,int i){return a&&i>=0&&i<*(int *)(a+0x10)?*(void **)(a+0x18+i*8):NULL;}
static int NAvatarInfo(void *env,void *opaque){
 NAvatarJob *j=opaque;uintptr_t b=NBase();
 uint8_t *c=*(void **)(b+NProfileCatalogs[j->variant]),*actor=*(void **)(b+NProfileActors[j->variant]);
 if(!c||!actor)return 0;
 j->atlas=NArrayObject(*(void **)(c+0xa0),j->hero);j->body=NArrayObject(*(void **)(actor+0xa0),j->hero);
 if(!j->body)return 0;
 for(int s=0;s<5;s++){
  if(j->parts[s]<0)continue;
  uint8_t *t=NProfileTemplate(j->variant,j->hero,s,j->parts[s]);if(!t)return 0;
  for(int k=0;k<6;k++){
   uint8_t *a=*(void **)(t+0x10+k*8);if(!a||*(int *)(a+0x10)<1)return 0;
   j->rect[s][k]=k<2?*(int16_t *)(a+0x14):*(int8_t *)(a+0x14);
  }
 }
 return 1;
}
static void NAvatarBlit(uint8_t *dest,const AGProfileIcon *src,int x,int y){
 for(int yy=0;yy<src->height;yy++)for(int xx=0;xx<src->width;xx++){
  /* Mirror the complete pose, including equipment, about its foot anchor. */
  int dx=79-(x+xx),dy=y+yy;if(dx<0||dx>=80||dy<0||dy>=80)continue;
  const uint8_t *s=src->rgba+((size_t)yy*src->width+xx)*4;uint8_t *d=dest+((size_t)dy*80+dx)*4;
  unsigned a=s[3],da=d[3],alpha=a+(da*(255-a)+127)/255;if(!alpha)continue;
  for(int k=0;k<3;k++)d[k]=(s[k]*a*255+d[k]*da*(255-a)+alpha*127)/(alpha*255);
  d[3]=alpha;
 }
}
int AGProfileAvatarRead(void *env,int v,int hero,const int parts[5],AGProfileIcon *out){
 if(!out)return 0;*out=(AGProfileIcon){.status=6,.iconID=-1};
 if(!env||v<0||v>=6||hero<0||hero>9||!parts)return 0;
 NAvatarJob j={.variant=v,.hero=hero};for(int i=0;i<5;i++){if(parts[i]<-1||parts[i]>32767)return 0;j.parts[i]=parts[i];}
 if(NRun(env,NAvatarInfo,&j)<=0)return 0;
 int bw=*(int *)(j.body+0x20),bh=*(int *)(j.body+0x24)/5;
 if(bw<1||bw>64||bh<1||bh>64)return 0;
 /* j5_.draw uses the character's equipment anchor, not the body PNG bounds. */
 int ew=hero==3?30:hero==6?29:hero==7?32:24,eh=hero==3||hero==7?32:24;
 out->rgba=calloc(80*80,4);if(!out->rgba)return 0;
 const int order[6]={0,4,5,1,2,3};
 for(int n=0;n<6;n++){
  int s=order[n];AGProfileIcon region={.status=6,.iconID=-1};
  if(s==5){
   if(!NReadImageRegion(env,j.body,0,0,bw,bh,-1,&region))goto failed;
   NAvatarBlit(out->rgba,&region,40-bw/2,64-bh);
  }else{
   int *r=j.rect[s];if(j.parts[s]<0||r[2]==0||r[3]==0)continue;
   if(!j.atlas||!NReadImageRegion(env,j.atlas,r[0],r[1],r[2],r[3],-1,&region))goto failed;
   NAvatarBlit(out->rgba,&region,40-ew/2+r[4]+18,64-eh+r[5]+40);
  }
  free(region.rgba);
 }
 out->width=out->height=80;out->status=0;return 1;
failed:free(out->rgba);out->rgba=NULL;return 0;
}
