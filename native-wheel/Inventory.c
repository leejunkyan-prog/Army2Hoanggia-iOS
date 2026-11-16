/* Inventory display order only. Server handles and quantities never change. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include "Inventory.h"
#include "CraftDiagnostics.h"
#define INV_LIMIT 4096
typedef struct { uint64_t key;int64_t quantity;uint8_t *item;int group,id,rank,fresh; } Entry;
typedef struct { int count,open,known;uint64_t hash;uintptr_t screen,connection;void *display;Entry *previous;unsigned login,notice; } InventoryState;
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
static int arrange(InventoryState *state,Entry *rows,int n,int mode){
    uint64_t hash=hashEntries(rows,n);
    if(!mode&&state->count==n&&state->hash==hash)return 0;
    if(!n)return 1;
    if(mode==1){qsort(rows,n,sizeof *rows,grouped);}
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
void AGInventoryPrepareRecipe(void *e,void *m,int v){(void)e;(void)m;(void)v;}
void AGInventoryReceive(void *m,int v){(void)m;(void)v;}
#else
#include <mach-o/dyld.h>
#include <pthread.h>
#include "NotesMap.h"
#include "InventoryMap.h"
extern int AGWheelGuard(void *,int (*)(void *,void *),void *,void *);
static uintptr_t base(void){return (uintptr_t)_dyld_get_image_header(0);}
static _Atomic unsigned logins[6],notices[6];
/* Observe complete replies without consuming the original Java stream.
   Cmd3 is a successful login even when the Session object is reused. Cmd45
   replaces the pending confirmation/wait with an informational OK dialog;
   the preceding cmd27 has already applied its inventory changes. */
void AGInventoryReceive(void *message,int v){
    if(!message||v<0||v>=6)return;
    uint8_t *m=message;int command=*(int8_t *)(m+0x30);
    if(command!=3&&command!=45)return;
    uint8_t *in=*(uint8_t **)(m+0x20),*array=in?*(uint8_t **)(in+0x10):NULL;
    if(!array)return;
    int cap=*(int *)(array+0x10),end=*(int *)(in+0x18),pos=*(int *)(in+0x20);
    if(pos<0||end<pos||end>cap)return;
    if(command==3){if(end-pos>=23)atomic_fetch_add(&logins[v],1);}
    else if(end-pos>=2){
        const uint8_t *p=array+0x14+pos;int length=(p[0]<<8)|p[1];
        if(length>0&&length==end-pos-2)atomic_fetch_add(&notices[v],1);
    }
}
/* Original service singleton getters and connection field, six PBs. Merely
   changing/reopening C6 does not start a new login session. */
static uintptr_t inventoryConnection(int v){
    static const uintptr_t slots[6]={0x207b870,0x20ab650,0x20d9350,0x2107040,0x2134d30,0x2162a20};
    uint8_t *clazz=*(void **)(base()+slots[v]),*service=clazz?*(void **)(clazz+0xa0):NULL;
    return service?*(uintptr_t *)(service+0x10):0;
}
static uint8_t *inventoryRoot(int v,uint8_t *screen){
    uint8_t *clazz=*(uint8_t **)(base()+inventoryMaps[v][2]);
    uint8_t *recipe=*(uint8_t **)(base()+recipeClasses[v]);
    if(!clazz)return NULL;
    if(!screen)return NULL;
    if(*(void **)screen==clazz)return screen;
    /* The real recipe screen inherits its commands at +0x10; that
       field is not a parent. Z5.i stores its inventory at +0x50. */
    if(recipe&&*(void **)screen==recipe){
        uint8_t *parent=*(uint8_t **)(screen+0x50);
        return parent&&*(void **)parent==clazz?parent:NULL;
    }
    /* Older callback wrappers use +0x10. Compare only known chest objects;
       never chase arbitrary command/string fields as a parent chain. */
    uint8_t *parent=*(uint8_t **)(screen+0x10);
    if(parent&&(parent==*(uint8_t **)(clazz+0xa0)||(uintptr_t)parent==inventories[v].screen))return parent;
    return NULL;
}
typedef struct {int v,options,before,after;} RecipeBinding;
static int bindRecipe(void *env,void *opaque){
    (void)env;RecipeBinding *j=opaque;
    uint8_t *canvas=*(uint8_t **)(base()+AGNotesMaps[j->v].canvas);
    uint8_t *clazz=*(uint8_t **)(base()+inventoryMaps[j->v][2]);
    if(!canvas||!clazz)return 0;
    uint8_t *root=inventoryRoot(j->v,*(uint8_t **)(canvas+0xb8));
    if(!root)return 0;
    j->before=*(void **)(clazz+0xa0)==root;
    /* Original cmd101 constructs a new C6 singleton while a recipe/result
       still retains the visible C6. The -18 dispatcher gates activation
       on identity with this singleton. Keep the attached screen as owner;
       do this on receive so no render tick or retry request is needed. */
    *(void **)(clazz+0xa0)=root;
    j->after=*(void **)(clazz+0xa0)==root;
    uint8_t *recipeClass=*(uint8_t **)(base()+recipeClasses[j->v]);
    uint8_t *recipe=recipeClass?*(uint8_t **)(recipeClass+0xa0):NULL;
    if(recipe&&j->options>0&&j->options<=127){
        int selected=*(int *)(recipe+0x58);
        /* The original parser replaces the option vector without resetting
           the selected level. A different recipe can have fewer options. */
        if(selected<0||selected>=j->options){
            *(int *)(recipe+0x58)=0;
            memset(recipe+0x5c,0,4*sizeof(int)); /* scroll target/current/easing */
        }
    }
    return 1;
}
void AGInventoryPrepareRecipe(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return;
    uint8_t *m=message;if(*(int8_t *)(m+0x30)!=-18)return;
    uint8_t *in=*(uint8_t **)(m+0x20),*array=in?*(uint8_t **)(in+0x10):NULL;
    if(!array)return;
    int cap=*(int *)(array+0x10),end=*(int *)(in+0x18),pos=*(int *)(in+0x20);
    if(pos<0||end<pos||end>cap||end-pos<10||end-pos>65535||!array[0x14+pos])return;
    RecipeBinding job={.v=v,.options=array[0x14+pos+9]};int ok=AGWheelGuard(env,bindRecipe,&job,(void *)(base()+0x1300d54));
    AGCraftRecipeBinding(v,ok,job.before,job.after);
}
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
static pthread_mutex_t inventoryMutex=PTHREAD_MUTEX_INITIALIZER;
static void inventoryOrder(void *env,int v,uint8_t *canvas,uint8_t *screen,int active){
    if(v<0||v>=6)return;
    InventoryState *state=&inventories[v];
    uintptr_t connection=inventoryConnection(v);
    unsigned login=atomic_load(&logins[v]),notice=atomic_load(&notices[v]);
    if(connection!=state->connection||login!=state->login){
        if(!env)return;
        unpin(env,state->display);free(state->previous);
        *state=(InventoryState){.connection=connection,.login=login,.notice=notice};
    }
    if(!active){
        /* A recipe child is still the same chest session. */
        if(state->open&&state->screen&&(uintptr_t)screen!=state->screen&&
           (uintptr_t)inventoryRoot(v,screen)==state->screen)return;
        if(!state->open||!env)return;
        unpin(env,state->display);
        state->display=NULL;state->open=0;state->screen=0;
        return;
    }
    if(!env||!canvas||!screen)return;
    if(state->open&&state->screen!=(uintptr_t)screen){
        unpin(env,state->display);state->display=NULL;state->open=0;state->screen=0;
    }
    /* Native C6.n rebinds +0x70 to the server vector even while a dialog is
       open. Restore the displayed order BEFORE deferring a rebuild; the
       callback's v() uses this same index several times during one tap. */
    if(state->open&&state->screen==(uintptr_t)screen&&state->display)
        *(void **)(screen+0x70)=state->display;
    /* +0xd4 is containsConsumables, set by the native bulk-combine callback
       and retained after its reply. It is not menu visibility: freezing on it
       hides every new gem until the chest is recreated. Use the actual menu
       visibility byte and the quantity-selection mode instead. */
    uint8_t *menu=*(uint8_t **)(canvas+0xe0);
    int result=notice!=state->notice;
    if((*(void **)(canvas+0x108)&&!result)||(menu&&menu[0x2c])||screen[0xd5])return;
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
    int reopening=!state->known;
    int changed=valid?arrange(state,rows,n,reopening?1:!state->open?2:0):0;
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
            state->open=state->known=1;state->screen=(uintptr_t)screen;
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
            /* APK promotes the result while its OK dialog is still visible
               and keeps the source stack selected if any remains. Recipe
               selection also stays bound to its existing callback. */
            int64_t selectedID=old?*(int64_t *)(old+0x80):-1;
            int recipeSelected=old&&old[0xbd]&&((selectedID>=69&&selectedID<=73)||(selectedID>=120&&selectedID<=129)||(selectedID>=238&&selectedID<=242));
            if(promoted&&!recipeSelected&&!result)index=0;
            *(int *)(screen+0xc8)=index;
            *(void **)(screen+0x90)=n?rows[index].item:NULL;
            uint8_t *clazz=*(uint8_t **)screen;
            if(clazz&&(promoted||reopening)){*(int *)(clazz+0xa8)=0;*(int *)(clazz+0xac)=0;}
            remember(state,rows,n);state->hash=hash;
            unpin(env,oldDisplay);
            if(n){Refresh job={v,screen};AGWheelGuard(env,refresh,&job,(void *)(base()+0x1300d54));}
        }else unpin(env,display.vector);
    }
    /* One result permits one snapshot, not a later confirmation. If Java
       allocation failed, retain the permit and retry on the next paint. */
    if(valid&&(!changed||state->hash==hash))state->notice=notice;
    free(rows);
}
/* Rebind in place before the original callback calls v() again. The recipe
   child and its parent are one chest session, including while a menu is up. */
void AGInventoryOrder(void *env,int v,uint8_t *canvas,uint8_t *screen,int active){
    if(!env||pthread_mutex_trylock(&inventoryMutex))return;
    inventoryOrder(env,v,canvas,screen,active);pthread_mutex_unlock(&inventoryMutex);
}
static void *inventoryResolve(void *env,void *opaque){
    if(!env||!opaque)return opaque;
    for(int v=0;v<6;v++){
        uint8_t *canvas=*(uint8_t **)(base()+AGNotesMaps[v].canvas);if(!canvas)continue;
        uint8_t *screen=*(uint8_t **)(canvas+0xb8),*vec=pool(v);
        void *clazz=*(void **)(base()+inventoryMaps[v][2]);
        if(!screen||!vec||!clazz)continue;
        screen=inventoryRoot(v,screen);
        if(!screen||*(void **)screen!=clazz)continue;
        uint8_t *display=*(uint8_t **)(screen+0x70),*items=display?elements(display):NULL;
        int index=*(int *)(screen+0xc8),count=display?*(int *)(display+0x24):0;
        if(!items||index<0||index>=count||count>INV_LIMIT||count>*(int *)(items+0x10))continue;
        uint8_t **slot=(uint8_t **)(items+0x18+index*8);
        if(!*slot||*slot!=opaque)continue;
        InventoryState *state=&inventories[v];
        if(state->open&&state->screen==(uintptr_t)screen&&state->display){
            /* Also repair an input callback between native rebind and the
               next render tick. Identify the PB by object identity before
               replacing the source-indexed item with the displayed one. */
            uint8_t *shown=elements(state->display);
            int shownCount=*(int *)((uint8_t *)state->display+0x24);
            if(!shown||index>=shownCount||shownCount>INV_LIMIT||
               shownCount>*(int *)(shown+0x10))continue;
            slot=(uint8_t **)(shown+0x18+index*8);
            *(void **)(screen+0x70)=state->display;
        }
        if(!*slot)continue;
        uint64_t wanted=key(*slot);
        /* All six PBs retain their own chest. An ID match in another PB
           must never substitute that PB's object into this callback. */
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
void *AGInventoryResolve(void *env,void *opaque){
    if(!env||pthread_mutex_trylock(&inventoryMutex))return opaque;
    void *result=inventoryResolve(env,opaque);pthread_mutex_unlock(&inventoryMutex);return result;
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
#ifdef AG_CRAFT_DIAGNOSTIC
static int vectorCount(uint8_t *vec){
    if(!vec)return -1;uint8_t *a=elements(vec);int n=*(int *)(vec+0x24);
    return a&&n>=0&&n<=INV_LIMIT&&n<=*(int *)(a+0x10)?n:-1;
}
static void diagnosticItem(uint8_t *p,int64_t *kind,int64_t *id,int64_t *quantity){
    *kind=0;*id=-1;*quantity=-1;if(!p)return;*kind=p[0xbd]?2:1;
    if(p[0xbd]){*id=*(int64_t *)(p+0x80);*quantity=*(int64_t *)(p+0x90);}
}
int AGInventoryCraftInspect(int v,void *opaque,int64_t d[CF_COUNT]){
    if(v<0||v>=6||!d)return 0;
    memset(d,0,CF_COUNT*sizeof *d);d[CF_SLOT_ID]=d[CF_CACHE_ID]=d[CF_SOURCE_QUANTITY]=-1;
    d[CF_SLOT_QUANTITY]=d[CF_CACHE_QUANTITY]=-1;
    uint8_t *canvas=*(uint8_t **)(base()+AGNotesMaps[v].canvas);
    uint8_t *clazz=*(uint8_t **)(base()+inventoryMaps[v][2]);if(!canvas||!clazz)return 0;
    uint8_t *current=*(uint8_t **)(canvas+0xb8),*root=*(uint8_t **)(clazz+0xa0);
    uint8_t *attached=inventoryRoot(v,current);if(attached)root=attached;
    if(!root||*(void **)root!=clazz)return 0;
    d[CF_OK]=1;d[CF_SCREEN]=current==root?1:inventoryRoot(v,current)==root?2:0;
    d[CF_PARENT_DEPTH]=d[CF_SCREEN]==2?1:0;
    InventoryState *state=&inventories[v];d[CF_STATE_OPEN]=state->open;d[CF_STATE_MATCH]=state->screen==(uintptr_t)root;
    d[CF_PRIVATE_DISPLAY]=state->display!=NULL;d[CF_SELECTED]=*(int *)(root+0xc8);
    d[CF_MENU_FLAG]=root[0xd4];d[CF_AMOUNT_FLAG]=root[0xd5];d[CF_MODAL]=*(void **)(canvas+0x108)!=NULL;
    uint8_t *menu=*(uint8_t **)(canvas+0xe0);
    if(menu){d[CF_MENU_VISIBLE]=menu[0x2c];d[CF_MENU_INDEX]=*(int *)(menu+0x18);d[CF_MENU_COUNT]=vectorCount(*(uint8_t **)(menu+0x10));}
    uint8_t *display=*(uint8_t **)(root+0x70),*source=pool(v);int n=vectorCount(display),count=vectorCount(source);
    d[CF_DISPLAY_COUNT]=n;d[CF_SOURCE_COUNT]=count;d[CF_DISPLAY_IS_SOURCE]=display&&display==source;
    d[CF_DISPLAY_IS_PRIVATE]=display&&display==state->display;
    int selected=(int)d[CF_SELECTED];uint8_t *slot=n>=0&&selected>=0&&selected<n?*(uint8_t **)(elements(display)+0x18+(size_t)selected*8):NULL;
    uint8_t *cached=*(uint8_t **)(root+0x90);
    diagnosticItem(slot,&d[CF_SLOT_KIND],&d[CF_SLOT_ID],&d[CF_SLOT_QUANTITY]);
    diagnosticItem(cached,&d[CF_CACHE_KIND],&d[CF_CACHE_ID],&d[CF_CACHE_QUANTITY]);
    d[CF_SLOT_EQUALS_CACHE]=slot&&slot==cached;d[CF_OPAQUE_IS_SLOT]=opaque&&opaque==slot;d[CF_OPAQUE_IS_CACHE]=opaque&&opaque==cached;
    uint8_t *a=source?elements(source):NULL;
    if(count>=0)for(int i=0;i<count;i++){
        uint8_t *p=*(uint8_t **)(a+0x18+(size_t)i*8);if(!p)continue;
        if(p==opaque)d[CF_OPAQUE_IN_SOURCE]=1;
        if(slot&&key(p)==key(slot)){
            d[CF_SOURCE_FOUND]=1;d[CF_SOURCE_EQUALS_SLOT]=p==slot;d[CF_SOURCE_EQUALS_CACHE]=p==cached;
            d[CF_SOURCE_QUANTITY]=p[0xbd]?*(int64_t *)(p+0x90):-1;
        }
    }
    d[CF_SNAPSHOT_STABLE]=pool(v)==source&&(!source||(elements(source)==a&&vectorCount(source)==count))&&*(uint8_t **)(root+0x70)==display;
    d[CF_SINGLETON_MATCH]=*(void **)(clazz+0xa0)==root;
    uint8_t *recipeClass=*(uint8_t **)(base()+recipeClasses[v]);
    uint8_t *recipe=recipeClass?*(uint8_t **)(recipeClass+0xa0):NULL;
    d[CF_RECIPE_ROWS]=recipe?vectorCount(*(uint8_t **)(recipe+0x48)):-1;
    d[CF_RECIPE_INDEX]=recipe?*(int *)(recipe+0x58):-1;
    d[CF_RECIPE_PARENT_MATCH]=recipe&&*(void **)(recipe+0x50)==root;
    return 1;
}
#endif
#endif




