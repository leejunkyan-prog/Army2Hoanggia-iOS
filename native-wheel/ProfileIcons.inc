/* Included by Notes77.m: use its existing native exception guard. These are
   read-only catalog/image lookups, independent of the logged-in inventory. */
#include "ProfileIcons.h"
static const uintptr_t NProfileCatalogs[6]={0x207fa20,0x20af620,0x20dd320,0x210b010,0x2138d00,0x21669f0};
static const uintptr_t NProfileConsumables[6]={0x2098970,0x20c7200,0x20f4ef0,0x2122be0,0x21508d0,0x217e5c0};
static uint8_t *NProfileVector(uint8_t *v,int *count){
    *count=0;if(!v)return NULL;
    uint8_t *a=*(void **)(v+0x18);int n=*(int *)(v+0x24);
    if(!a||n<0||n>4096||n>*(int *)(a+0x10))return NULL;
    *count=n;return a+0x18;
}
typedef struct {int variant,hero,slot,id;AGProfileIcon *out;void *imageRoot,*array;} NProfileIconJob;
static int NProfileIcon(void *env,void *opaque){
    NProfileIconJob *j=opaque;AGProfileIcon *out=j->out;uintptr_t base=NBase();
    uint8_t *clazz=*(void **)(base+NProfileCatalogs[j->variant]),*image=NULL;
    int nh=0;uint8_t **heroes=clazz?(void *)NProfileVector(*(void **)(clazz+0xb0),&nh):NULL;
    if(j->slot<5){
        uint8_t *item=NULL;
        for(int h=0;heroes&&h<nh&&!item;h++){
            uint8_t *hero=heroes[h];if(!hero||(int8_t)hero[0x1a]!=j->hero)continue;
            int ns=0;uint8_t **slots=(void *)NProfileVector(*(void **)(hero+0x10),&ns);
            for(int s=0;slots&&s<ns&&!item;s++){
                uint8_t *slot=slots[s];if(!slot||(int8_t)slot[0x18]!=j->slot)continue;
                int ni=0;uint8_t **items=(void *)NProfileVector(*(void **)(slot+0x10),&ni);
                for(int i=0;items&&i<ni;i++)if(items[i]&&*(int64_t *)(items[i]+0x80)==j->id){item=items[i];break;}
            }
        }
        if(!item){out->status=1;return 0;}
        int64_t icon=*(int64_t *)(item+0x88);if(icon<0||icon>32767){out->status=2;return 0;}
        out->iconID=(int)icon;
        // Exactly the icon cache/key used by the original j5_.paint method.
        void *cache=((void *(*)(void *))(base+0xc46b40))(env);
        void *key=((void *(*)(void *,int))(base+0xab216c))(env,(int)icon);
        if(cache&&key)image=((void *(*)(void *,void *,void *))(base+0xbc88a0))(env,cache,key);
    }else{
        // Original consumable/costume image registry: entry ID at +0x18,
        // image at +0x10. No own-account quantities or stats are consulted.
        uint8_t *c=*(void **)(base+NProfileConsumables[j->variant]);int count=0;
        uint8_t **items=c?(void *)NProfileVector(*(void **)(c+0xa0),&count):NULL;
        for(int i=0;items&&i<count;i++)if(items[i]&&*(int64_t *)(items[i]+0x18)==j->id){image=*(void **)(items[i]+0x10);break;}
    }
    if(!image){out->status=3;return 0;}
    void **jni=*(void ***)env;
    j->imageRoot=((void *(*)(void *,void *))jni[21])(env,image);if(!j->imageRoot)return 0;
    int w=*(int *)(image+0x20),h=*(int *)(image+0x24);
    if(w<1||h<1||w>128||h>128){out->status=4;return 0;}
    uint8_t *pixels=*(void **)(image+0x10);
    if(!pixels){
        if(!*(void **)(image+0x18)){out->status=5;return 0;}
        j->array=((void *(*)(void *,int))jni[179])(env,w*h);if(!j->array)return 0;
        // javax.microedition.lcdui.v.l([IIIIIII)V, verified in AOT metadata.
        // Its Pixmap.getPixel values use libGDX RGBA8888 ordering.
        ((void (*)(void *,void *,void *,int,int,int,int,int,int))(base+0xc48ea0))(env,image,j->array,0,w,0,0,w,h);
        pixels=j->array;
    }
    if(*(int *)(pixels+0x10)<w*h){out->status=5;return 0;}
    out->rgba=malloc((size_t)w*h*4);if(!out->rgba)return 0;
    const uint32_t *rgba=(void *)(pixels+0x14);
    for(int i=0;i<w*h;i++){
        uint32_t p=rgba[i];out->rgba[i*4]=p>>24;out->rgba[i*4+1]=p>>16;out->rgba[i*4+2]=p>>8;out->rgba[i*4+3]=p;
    }
    out->width=w;out->height=h;out->status=0;return 1;
}
int AGProfileIconRead(void *env,int variant,int hero,int slot,int id,AGProfileIcon *out){
    if(!out)return 0;*out=(AGProfileIcon){.status=6,.iconID=-1};
    if(!env||variant<0||variant>=6||hero<0||hero>9||slot<0||slot>5||id<0||id>32767)return 0;
    NProfileIconJob j={.variant=variant,.hero=hero,.slot=slot,.id=id,.out=out};
    int result=NRun(env,NProfileIcon,&j);void **jni=*(void ***)env;
    if(j.array)((void (*)(void *,void *))jni[23])(env,j.array);
    if(j.imageRoot)((void (*)(void *,void *))jni[22])(env,j.imageRoot);
    if(result<=0){free(out->rgba);out->rgba=NULL;if(result<0)out->status=6;return 0;}return 1;
}
