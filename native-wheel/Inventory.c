/* Inventory display order only. Server handles and quantities never change. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "Inventory.h"
#define INV_LIMIT 4096
typedef struct { uint64_t key;int64_t quantity;uint8_t *item;int group,id,rank,fresh; } Entry;
typedef struct { int count,open;uint64_t hash;uintptr_t screen;void *display;Entry *previous; } InventoryState;
static InventoryState inventories[6];
static uint64_t key(const uint8_t *p){return p[0xbd]?(UINT64_C(1)<<63)|(uint64_t)*(const int64_t *)(p+0x80):(uint32_t)*(const int *)(p+0xb0);}
static int group(const uint8_t *p){
    if(!p[0xbd])return 0; /* Includes ordinary gear and costume sets. */
    int64_t id=*(const int64_t *)(p+0x80);
    if((id>=0&&id<50)||(id>=130&&id<=134))return 1;
    if(id>=100&&id<=109)return 2;
    if(id==50||id==54||id==90||(id>=57&&id<=61)||(id>=69&&id<=73)||(id>=120&&id<=129)||(id>=238&&id<=242))return 3;
    return 4;
}
static int byKey(const void *a,const void *b){uint64_t x=((const Entry *)a)->key,y=((const Entry *)b)->key;return (x>y)-(x<y);}
static int grouped(const void *aa,const void *bb){
    const Entry *a=aa,*b=bb;
    if(a->group!=b->group)return a->group-b->group;
    if(a->group&&a->id!=b->id)return (a->id>b->id)-(a->id<b->id);
    return a->rank-b->rank;
}
static int updated(const void *aa,const void *bb){const Entry *a=aa,*b=bb;if(a->fresh!=b->fresh)return b->fresh-a->fresh;return a->rank-b->rank;}
static uint64_t hashEntries(const Entry *p,int n){uint64_t h=1469598103934665603ULL;for(int i=0;i<n;i++){h=(h^p[i].key)*1099511628211ULL;h=(h^(uint64_t)p[i].quantity)*1099511628211ULL;h=(h^(uintptr_t)p[i].item)*1099511628211ULL;}return h;}
/* Pure ordering step, shared by the native bridge and the regression fixture. */
static int arrange(InventoryState *state,Entry *rows,int n,int reopening){
    uint64_t hash=hashEntries(rows,n);
    if(!reopening&&state->count==n&&state->hash==hash)return 0;
    if(!n)return 1;
    if(reopening){qsort(rows,n,sizeof *rows,grouped);}
    else{
        for(int i=0;i<n;i++){
            const Entry *old=state->count?bsearch(&rows[i],state->previous,state->count,sizeof *rows,byKey):NULL;
            rows[i].fresh=!old||rows[i].quantity>old->quantity;
            rows[i].rank=old?old->rank:state->count+i;
        }
        qsort(rows,n,sizeof *rows,updated);
    }
    return 1;
}
static void remember(InventoryState *state,Entry *rows,int n){
    Entry *next=n?malloc((size_t)n*sizeof *next):NULL;
    if(n&&!next)return;
    state->hash=hashEntries(rows,n);
    for(int i=0;i<n;i++){next[i]=rows[i];next[i].rank=i;next[i].item=NULL;}
    if(n)qsort(next,n,sizeof *next,byKey);
    free(state->previous);state->previous=next;state->count=n;
}
#ifdef AG_WHEEL_PREVIEW
void AGInventoryOrder(void *e,int v,uint8_t *c,uint8_t *s,int active){(void)e;(void)v;(void)c;(void)s;(void)active;}
void *AGInventoryResolve(void *e,void *p){(void)e;return p;}
int AGInventoryGeometry(int v,int *out){(void)v;(void)out;return 0;}
#else
#include <mach-o/dyld.h>
#include "NotesMap.h"
#include "InventoryMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static uintptr_t base(void){return (uintptr_t)_dyld_get_image_header(0);}
static uint8_t *pool(int v){uint8_t *p=*(uint8_t **)(base()+inventoryMaps[v][0]);return p?*(uint8_t **)(p+0xa8):NULL;}
/* java.util.Vector.elementData follows modCount and its alignment padding.
   The AOT constructor and elementAt both access it at +0x18. */
static uint8_t *elements(uint8_t *vector){return *(uint8_t **)(vector+0x18);}
typedef struct {int v;uint8_t *screen;} Refresh;
static int refresh(void *e,void *opaque){Refresh *j=opaque;((void (*)(void *,void *))(base()+inventoryMaps[j->v][1]))(e,j->screen);return 1;}
static void *pin(void *e,void *p){return p?((void *(*)(void *,void *))(*(void ***)e)[21])(e,p):NULL;}
static void unpin(void *e,void *p){if(p)((void (*)(void *,void *))(*(void ***)e)[22])(e,p);}
typedef struct {Entry *rows;int count;void *vector;} Display;
static int makeDisplay(void *e,void *opaque){
    Display *j=opaque;uintptr_t b=base();
    void *volatile vec=((void *(*)(void *))(b+0xbe3f1c))(e);
    if(!vec)return 0;
    ((void (*)(void *,void *,int))(b+0xbe6ba0))(e,vec,j->count);
    for(int i=0;i<j->count;i++)((void (*)(void *,void *,void *))(b+0x1dfcac))(e,vec,j->rows[i].item);
    j->vector=pin(e,vec);return j->vector!=NULL;
}
void AGInventoryOrder(void *env,int v,uint8_t *canvas,uint8_t *screen,int active){
    if(v<0||v>=6)return;
    InventoryState *state=&inventories[v];
    if(!active){
        /* Z5.i(env,screen,parent) stores the parent at +0x10. A recipe
           child is still the same chest session, not an explicit close. */
        if(state->open&&screen&&state->screen&&*(uintptr_t *)(screen+0x10)==state->screen)return;
        if(!state->open||!env)return;
        unpin(env,state->display);
        free(state->previous);
        *state=(InventoryState){0};
        return;
    }
    /* Menus, amount entry, craft progress and result dialogs keep their target. */
    if(!env||!canvas||!screen||*(void **)(canvas+0x108)||screen[0xd4]||screen[0xd5])return;
    /* The render callback must never wait for the server Vector's Java
       monitor: its owner may itself be waiting for a render-thread task.
       Sort a private display vector and leave the server collection intact. */
    uint8_t *volatile vec=pool(v);if(!vec)return;
    uint8_t *volatile array=elements(vec);int n=*(int *)(vec+0x24);
    if(!array||n<0||n>INV_LIMIT||n>*(int *)(array+0x10))return;
    uint8_t **objects=(uint8_t **)(array+0x18);Entry *rows=n?calloc((size_t)n,sizeof *rows):NULL;
    if(n&&!rows)return;
    // Keep the source and its item handles on the game stack across Java calls.
    uint8_t *volatile roots[n?n:1];
    int valid=1;uint64_t selected=0;int index=*(int *)(screen+0xc8);
    uint8_t *old=*(uint8_t **)(screen+0x90);if(old)selected=key(old);
    for(int i=0;i<n;i++){
        uint8_t *item=objects[i];if(!item){valid=0;break;}
        roots[i]=item;
        rows[i]=(Entry){.key=key(item),.quantity=item[0xbd]?*(int64_t *)(item+0x90):1,.item=item,.group=group(item),.id=(int)*(int64_t *)(item+0x80),.rank=i};
    }
    if(pool(v)!=vec||elements(vec)!=array||*(int *)(vec+0x24)!=n)valid=0;
    for(int i=0;valid&&i<n;i++)if(objects[i]!=roots[i])valid=0;
    uint64_t hash=valid?hashEntries(rows,n):0;
    int reopening=!state->open||state->screen!=(uintptr_t)screen;
    int changed=valid?arrange(state,rows,n,reopening):0;
    if(valid&&!changed&&state->display){
        // Native C6.n rebinds to the source every frame. Reuse our existing
        // display vector here, before the input and paint paths use it.
        *(void **)(screen+0x70)=state->display;
        if(n&&index>=0&&index<n){
            uint8_t *items=elements(state->display);
            uint8_t *selectedItem=*(uint8_t **)(items+0x18+index*8);
            if(old!=selectedItem){
                Refresh job={v,screen};
                AGWheelGuard(env,refresh,&job,(void *)(base()+0x1300d54));
            }
        }
    }else if(valid&&changed){
        Display display={rows,n,NULL};
        int ready=AGWheelGuard(env,makeDisplay,&display,(void *)(base()+0x1300d54))>0;
        ready=ready&&pool(v)==vec&&elements(vec)==array&&*(int *)(vec+0x24)==n;
        for(int i=0;ready&&i<n;i++)if(objects[i]!=roots[i])ready=0;
        if(ready){
            void *oldDisplay=state->display;
            state->display=display.vector;
            state->open=1;state->screen=(uintptr_t)screen;
            *(void **)(screen+0x70)=display.vector;
            index=0;
            int promoted=0,found=0;
            for(int i=0;i<n;i++){
                if(rows[i].key==selected){index=i;found=1;}
                promoted|=rows[i].fresh;
            }
            /* New gear can move to the front without changing the target
               of the recipe callback. That callback calls native v() again
               when tapped, so changing index here silently changes its item. */
            if(reopening||!found)index=0;
            *(int *)(screen+0xc8)=index;
            *(void **)(screen+0x90)=n?rows[index].item:NULL;
            uint8_t *clazz=*(uint8_t **)screen;
            if(clazz&&(promoted||reopening)){*(int *)(clazz+0xa8)=0;*(int *)(clazz+0xac)=0;}
            remember(state,rows,n);state->hash=hash;
            unpin(env,oldDisplay);
            if(n){Refresh job={v,screen};AGWheelGuard(env,refresh,&job,(void *)(base()+0x1300d54));}
        }else unpin(env,display.vector);
    }
    free(rows);
}
/* Rebind in place before the original callback calls v() again. The recipe
   child and its parent are one chest session, including while a menu is up. */
void *AGInventoryResolve(void *env,void *opaque){
    if(!env||!opaque)return opaque;uint8_t *item=opaque;uint64_t wanted=key(item);
    for(int v=0;v<6;v++){
        uint8_t *canvas=*(uint8_t **)(base()+AGNotesMaps[v].canvas);if(!canvas)continue;
        uint8_t *screen=*(uint8_t **)(canvas+0xb8),*vec=pool(v);
        void *clazz=*(void **)(base()+inventoryMaps[v][2]);
        if(!screen||!vec||!clazz)continue;
        for(int depth=0;screen&&*(void **)screen!=clazz&&depth<4;depth++)screen=*(uint8_t **)(screen+0x10);
        if(!screen||*(void **)screen!=clazz)continue;
        uint8_t *display=*(uint8_t **)(screen+0x70),*items=display?elements(display):NULL;
        int index=*(int *)(screen+0xc8),count=display?*(int *)(display+0x24):0;
        if(!items||index<0||index>=count||count>INV_LIMIT||count>*(int *)(items+0x10))continue;
        uint8_t **slot=(uint8_t **)(items+0x18+index*8);
        /* All six PBs retain their own chest. An ID match in another PB
           must never substitute that PB's object into this callback. */
        if(!*slot||*slot!=opaque||key(*slot)!=wanted)continue;
        uint8_t *data=elements(vec);int n=*(int *)(vec+0x24);
        if(!data||n<0||n>INV_LIMIT||n>*(int *)(data+0x10))continue;
        uint8_t **rows=(uint8_t **)(data+0x18);
        for(int i=0;i<n;i++)if(rows[i]&&key(rows[i])==wanted){
            *slot=rows[i];*(void **)(screen+0x90)=rows[i];
            return rows[i];
        }
    }
    return opaque;
}
int AGInventoryGeometry(int v,int *out){
    if(v<0||v>=6||!out)return 0;
    uint8_t *canvas=*(uint8_t **)(base()+AGNotesMaps[v].canvas),*clazz=*(uint8_t **)(base()+inventoryMaps[v][2]);
    uint8_t *screen=clazz?*(uint8_t **)(clazz+0xa0):NULL;
    if(!canvas||!screen||*(void **)screen!=clazz)return 0;
    int width=*(int *)(canvas+0x130),x=*(int *)(screen+0x50)-7,y=*(int *)(screen+0x54),w=*(int *)(screen+0x58),h=*(int *)(screen+0x5c),cols=*(int *)(screen+0xc0),cell=*(int *)(screen+0xb8);
    if(width<160||width>4096||x<0||y<0||w<120||w>width||x+w>width||h<120||h>4096||cols<3||cols>7||cell<16||cell*cols>w)return 0;
    int values[]={width,x,y,w,h,cols,cell};memcpy(out,values,sizeof values);return 1;
}
#endif

