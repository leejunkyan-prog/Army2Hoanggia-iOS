#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <string.h>
#include "Spectator.h"
#include "SpectatorNative.h"
#include "WatchTrace.h"
#import "WatchSurface.h"
#include "Lobby.h"
#import "GameViewport.h"

typedef NS_ENUM(int, WatchPhase) { Offered, WaitingForMatch, InMatch };
typedef NS_ENUM(int, WatchAction) { NoAction, Accept };
typedef NS_ENUM(int, WatchReceive) { PassToGame, Consumed, Snapshot, MatchEnded, LiveBeforeReady, ObserveFrame, ReplayFrame };

@interface ArmyWatch : UIViewController <WKScriptMessageHandler, WKNavigationDelegate>
@property(nonatomic) int variant;
@property(nonatomic) uintptr_t connection;
@property(nonatomic) uint8_t room, area;
@property(nonatomic,copy) NSData *ticket;
@property(nonatomic,copy) NSString *question;
@property(nonatomic) WatchPhase phase;
@property(nonatomic) WatchAction action;
@property(nonatomic) NSTimeInterval deadline;
@property(nonatomic,weak) UIWindow *window;
@property(nonatomic,weak) UIWindow *previous;
@property(nonatomic,strong) WKWebView *web;
@property(nonatomic,strong) NSMutableArray *pending;
@property(nonatomic,strong) NSTimer *watchdog;
@property(nonatomic) NSUInteger pendingBytes;
@property(nonatomic) BOOL webReady, delivering, retryScheduled, snapshotReceived, endReceived;
@property(nonatomic) BOOL battlefield, menuVisible, nativeStarted;
@property(nonatomic) BOOL auxiliary;
@property(nonatomic) BOOL keypadCaptured;
@property(nonatomic) int shownAngle;
@property(nonatomic) int switchToPB;
@property(nonatomic) NSTimeInterval traceSavedAt;
- (void)show;
- (void)close;
- (void)flush;
- (void)accept;
- (void)cancel;
- (void)updatePhase;
- (void)checkDeadline;
@end

static ArmyWatch *current;
static atomic_bool active;
static atomic_int activeVariant;
static atomic_bool watching[6];
static atomic_bool nativeCleanup[6];
static atomic_int snapshotCalls[6];
static atomic_int pendingPB[6];
static ArmyWatch *pendingLeave[6];
static ArmyWatch *closingWatch[6];
int AGViewerActive(int v){
    return v>=0&&v<6&&(atomic_load(&active)&&atomic_load(&activeVariant)==v);
}
static bool heldKeys[6][256];
static atomic_uintptr_t nativeWait[6];
static uintptr_t battlefieldSession[6];
static NSTimeInterval battlefieldUntil[6];
static NSTimeInterval now(void) { return NSProcessInfo.processInfo.systemUptime; }
static void updateCamera(ArmyWatch *watch);

int AGViewerInput(int variant,int kind,int code) {
    if(variant<0||variant>=6)return 0;
    if((unsigned)kind>1)return atomic_load(&nativeCleanup[variant])||(AGViewerActive(variant)&&!AGNativeWatchAux(variant));
    ArmyWatch *watch;
    const unsigned index=(unsigned)code+128;
    @synchronized(ArmyWatch.class){
        if(kind==1&&index<256&&heldKeys[variant][index]){
            heldKeys[variant][index]=false;
            if(AGNativeWatchAvailable())AGNativeWatchCamera(variant,kind,code);
            return 1;
        }
        watch=current;
        if(!watch||watch.variant!=variant)return atomic_load(&nativeCleanup[variant]);
        if(watch.phase==InMatch&&AGNativeWatchAux(variant))return 0;
        BOOL repeated=kind==0&&index<256&&heldKeys[variant][index];
        if(kind==0&&index<256)heldKeys[variant][index]=true;
        if(repeated&&(code==-6||code==-7||code==-21||code==-22))return 1;
        if(kind==0&&watch.phase==InMatch&&watch.snapshotReceived){
            // Native pad: F1=-6 / F2=-7. Hardware aliases are -21/-22.
            // Both pairs go through watchKey: left opens Menu, right Camera,
            // with the normal select/back behavior when a menu is open.
            BOOL direction=(code>=-4&&code<=-1)||code=='2'||code=='4'||code=='6'||code=='8';
            if(direction&&AGNativeWatchFree(variant)&&!watch.menuVisible)
                AGNativeWatchCamera(variant,kind,code);
        }
        if(kind==0&&watch.phase==WaitingForMatch&&
           (code==-7||code==-22||code==-11||code=='R'||code=='r'||code==27)){
            [watch cancel];
            return 1;
        }
    }
    if(kind==0)dispatch_async(dispatch_get_main_queue(),^{
        @synchronized(ArmyWatch.class){if(current!=watch)return;}
        if(watch.webReady){
            [watch.web evaluateJavaScript:[NSString stringWithFormat:@"watchKey(%d)",code] completionHandler:nil];
        }else if(watch.phase==Offered&&(code==-6||code==-5||code==-21||code=='L'||code=='l'||code==13||code==10||code=='5'||code=='F'||code=='f')){
            [watch accept];
        }else if(watch.phase==Offered&&(code==-7||code==-22||code==-11||code=='R'||code=='r'||code==27)){
            [watch cancel];
        }
    });
    return 1;
}
static UIWindow *visibleHost(void) {
    UIApplication *app=UIApplication.sharedApplication;
    UIWindow *key=app.keyWindow;
    if(key && !key.hidden && key.rootViewController)return key;
    if(@available(iOS 13.0,*)){
        for(UIScene *scene in app.connectedScenes){
            if(![scene isKindOfClass:UIWindowScene.class] || scene.activationState!=UISceneActivationStateForegroundActive)continue;
            for(UIWindow *window in ((UIWindowScene *)scene).windows)
                if(!window.hidden && window.rootViewController && window.windowLevel==UIWindowLevelNormal)return window;
        }
    }
    for(UIWindow *window in app.windows)
        if(!window.hidden && window.rootViewController && window.windowLevel==UIWindowLevelNormal)return window;
    return nil;
}
void AGViewerExpectBattlefield(int variant,uintptr_t connection) {
    if(variant<0||variant>=6||!connection)return;
    @synchronized(ArmyWatch.class){battlefieldSession[variant]=connection;battlefieldUntil[variant]=now()+15;}
}
static void screen(ArmyWatch *w) { dispatch_async(dispatch_get_main_queue(),^{ [w show]; }); }
static void updateCamera(ArmyWatch *watch) {
    @synchronized(ArmyWatch.class){
        if(current!=watch||watch.phase!=InMatch||!watch.snapshotReceived||watch.auxiliary||watch.menuVisible)return;
        int free=AGNativeWatchToggleCamera(watch.variant);
        [watch.web evaluateJavaScript:[NSString stringWithFormat:@"watchCameraMode(%d)",free] completionHandler:nil];
    }
}
static void finish(ArmyWatch *w) {
    if(current!=w)return;
    if(AGNativeWatchAvailable()&&w.phase!=Offered)atomic_store(&nativeCleanup[w.variant],true);
    current=nil;atomic_store(&active,false);
    atomic_store(&watching[w.variant],false);
    AGNativeWatchClearCameraKeys(w.variant);
    if(w.switchToPB)atomic_store(&pendingPB[w.variant],w.switchToPB);
    closingWatch[w.variant]=w;
    if(!atomic_load(&nativeCleanup[w.variant])&&!w.battlefield){
        closingWatch[w.variant]=nil;
        dispatch_async(dispatch_get_main_queue(),^{[w close];});
    }
}
static void leave(ArmyWatch *w) {
    if(w.endReceived){finish(w);return;}
    if(w.phase!=Offered&&w.action!=Accept)pendingLeave[w.variant]=w;
    finish(w);
}
static void advanceWatch(ArmyWatch *w,NSTimeInterval time) {
    if(!w.deadline||time<w.deadline)return;
    leave(w);
}
static void watchReady(ArmyWatch *w){
    if(w.phase!=InMatch||w.snapshotReceived)return;
    w.snapshotReceived=YES;
    w.deadline=0;
    screen(w);
}
int AGViewerStillWatching(int variant) {
    return variant>=0&&variant<6&&atomic_load(&watching[variant]);
}
static NSData *readBody(void *message) {
    // The same HG78 DataInputStream layout used by Notes77 and Corpse.
    const uint8_t *in=*(const uint8_t **)((uint8_t *)message+0x20);
    if(!in)return nil;
    const uint8_t *array=*(const uint8_t **)(in+0x10);
    if(!array)return nil;
    int capacity=*(const int *)(array+0x10),end=*(const int *)(in+0x18),pos=*(const int *)(in+0x20);
    if(pos<0 || pos>end || end>capacity || end-pos>65535)return nil;
    return [NSData dataWithBytes:array+0x14+pos length:(NSUInteger)(end-pos)];
}
static BOOL combatPacket(int cmd) {
    switch(cmd) {
        case 8: case 9: case 14: case 20: case 21: case 22: case 24: case 25: case 26:
        case 50: case 51: case 52: case 76: case 80: case 83: case 84: case 89: case 93:
        case 95: case 96: case 97: case 100: case 106: case 107: case 108: case 109:
        case 113: case 124: return YES;
        default:return NO;
    }
}
static WatchReceive receiveState(void *env,void *message,int variant,NSData *__strong *nativePacket,ArmyWatch *__strong *owner) {
    if(!env||!message||variant<0||variant>=6)return PassToGame;
    int cmd=*(const int8_t *)((const uint8_t *)message+0x30);
    if(cmd!=-102&&!atomic_load(&active))
        return atomic_load(&nativeCleanup[variant])&&combatPacket(cmd)&&cmd!=8&&cmd!=20?Consumed:PassToGame;
    @autoreleasepool {
        @synchronized(ArmyWatch.class) {
            ArmyWatch *w=current;
            if(cmd!=-102 && (!w || w.variant!=variant))return 0;
            if(cmd==3 || cmd==-4){finish(w);return 0;}
            if(cmd==45 && w.phase==WaitingForMatch){finish(w);return 0;}
            if(cmd!=-102){
                if(w.phase!=InMatch||!combatPacket(cmd))return 0;
                if(AGNativeWatchAvailable()){
                    if(cmd==20)return 1;
                    if(cmd==51&&w.nativeStarted&&!w.snapshotReceived){
                        *nativePacket=readBody(message);*owner=w;
                        return ReplayFrame;
                    }
                    if(w.nativeStarted&&!w.snapshotReceived&&(cmd==21||cmd==22||cmd==84)){
                        // Some servers omit the final clock packet. The first
                        // live move or shot follows the complete snapshot.
                        // Complete before the original dispatcher sees it.
                        *owner=w;
                        return LiveBeforeReady;
                    }
                    if(cmd==8||cmd==24||cmd==22||cmd==84){
                        *nativePacket=readBody(message);
                        *owner=w;
                        return ObserveFrame;
                    }
                    return 0;
                }
            }
            NSData *body=readBody(message);
            if(!body){if(w && w.variant==variant)leave(w);return 1;}
            const uint8_t *p=body.bytes;NSUInteger n=body.length;
            if(cmd==-102) {
                if(n<4||p[0]!=0x53||p[1]!=0x50||p[2]!=1)return 1;
                if(p[3]==0) {
                    if(n<16 || p[4]>1 || n!=16+(NSUInteger)(p[14]*256+p[15]))return 1;
                    if((w&&w.phase!=Offered)||atomic_load(&nativeCleanup[variant]))return 1;
                    uintptr_t conn=AGViewerConnection(env,variant);
                    if(!conn)return 1;
                    uintptr_t wait=AGViewerWaitToken(variant);
                    if(wait)atomic_store(&nativeWait[variant],wait);
                    BOOL battlefield=battlefieldUntil[variant]>now()&&battlefieldSession[variant]==conn;
                    w=[ArmyWatch new];w.variant=variant;w.connection=conn;w.room=p[4];w.area=p[5];
                    w.battlefield=battlefield;
                    if(battlefield)battlefieldUntil[variant]=0;
                    w.ticket=[body subdataWithRange:NSMakeRange(6,8)];
                    w.question=[[NSString alloc] initWithBytes:p+16 length:n-16 encoding:NSUTF8StringEncoding]?:@"Bạn muốn xem trận đang diễn ra?";
                    w.pending=[NSMutableArray array];w.phase=Offered;w.deadline=now()+60;w.shownAngle=-1;
                    if(current){ArmyWatch *previous=current;dispatch_async(dispatch_get_main_queue(),^{[previous close];});}
                    current=w;atomic_store(&activeVariant,variant);atomic_store(&active,true);screen(w);return 1;
                }
                if(!w && p[3]==3 && n==21 && p[4]<=1 && !atomic_load(&nativeCleanup[variant]) &&
                   battlefieldUntil[variant]>now() && battlefieldSession[variant]==AGViewerConnection(env,variant)){
                    w=[ArmyWatch new];w.variant=variant;w.connection=battlefieldSession[variant];
                    w.room=p[4];w.area=p[5];w.battlefield=YES;
                    w.ticket=[body subdataWithRange:NSMakeRange(6,8)];
                    w.pending=[NSMutableArray array];w.phase=WaitingForMatch;
                    w.deadline=now()+15;w.shownAngle=-1;
                    current=w;atomic_store(&activeVariant,variant);atomic_store(&active,true);battlefieldUntil[variant]=0;
                }
                if(!w || w.variant!=variant)return 1;
                if(p[3]==6){
                    if(n!=12||memcmp(p+4,w.ticket.bytes,8)||w.endReceived)return 1;
                    if(AGNativeWatchAvailable()){*nativePacket=body;*owner=w;return MatchEnded;}
                    if(w.phase!=InMatch||!w.snapshotReceived){finish(w);return 1;}
                    // Keep the last shot and its HP update in the same queue as earlier frames.
                    w.endReceived=YES;w.deadline=now()+10;
                }else if(p[3]==3){
                    if(n!=21||p[4]!=w.room||p[5]!=w.area||memcmp(p+6,w.ticket.bytes,8))return 1;
                    if(w.phase!=WaitingForMatch)return 1;
                    w.phase=InMatch;w.deadline=now()+20;
                    atomic_store(&watching[variant],true);
                    screen(w);
                }else if(p[3]!=4&&p[3]!=5&&p[3]!=7)return 1;
                if(w.phase!=InMatch)return 1;
                if(!w.snapshotReceived)w.deadline=now()+20;
                if(p[3]==7&&!AGNativeWatchAvailable())w.snapshotReceived=YES;
            }
            if(AGNativeWatchAvailable()){*nativePacket=body;*owner=w;return Snapshot;}
            if(w.pending.count>=4096 || w.pendingBytes+n>24*1024*1024){leave(w);return 1;}
            [w.pending addObject:@[@(cmd),body]];
            w.pendingBytes+=n;
            if(w.pending.count==1)dispatch_async(dispatch_get_main_queue(),^{[w flush];});
            return 1;
        }
    }
}
int AGViewerReceive(void *env,void *message,int variant){
    @autoreleasepool {
        if(env&&message&&variant>=0&&variant<6&&AGViewerActive(variant)){
            int cmd=*(const int8_t *)((const uint8_t *)message+0x30),op=-1;
            if(cmd==-102){NSData *body=readBody(message);if(body.length>=4)op=((const uint8_t *)body.bytes)[3];}
            AGNativeWatchTracePacket(variant,cmd,op);
        }
        NSData *packet=nil;ArmyWatch *owner=nil;
        WatchReceive result=receiveState(env,message,variant,&packet,&owner);
        if(result==PassToGame||result==Consumed)return result;
        const uint8_t *p=packet.bytes;
        // Texture creation may hand off to the GDX render thread. Never hold
        // the UI/state monitor while waiting for the original game routines.
        if(result==MatchEnded){
            @synchronized(ArmyWatch.class){if(current==owner){owner.endReceived=YES;finish(owner);}}
        }else if(result==LiveBeforeReady){
            int cmd=*(const int8_t *)((const uint8_t *)message+0x30);
            NSData *frame=readBody(message);
            if(frame)AGNativeWatchObserve(variant,cmd,frame.bytes,frame.length);
            if(!AGNativeWatchFinishSnapshot(env,variant)){
                @synchronized(ArmyWatch.class){if(current==owner)leave(owner);}
                return 1;
            }
            @synchronized(ArmyWatch.class){
                if(current!=owner||owner.phase!=InMatch)return 1;
                watchReady(owner);
            }
            return 0;
        }else if(result==ReplayFrame){
            int cmd=*(const int8_t *)((const uint8_t *)message+0x30);
            return packet?AGNativeWatchReplay(env,variant,cmd,p,packet.length):0;
        }else if(result==ObserveFrame){
            int cmd=*(const int8_t *)((const uint8_t *)message+0x30);
            if(packet)AGNativeWatchObserve(variant,cmd,p,packet.length);
            return 0;
        }else{
            @synchronized(ArmyWatch.class){
                if(current!=owner||owner.phase!=InMatch)return 1;
                atomic_fetch_add(&snapshotCalls[variant],1);
            }
            int ok=AGNativeWatchPacket(env,variant,p,packet.length);
            atomic_fetch_sub(&snapshotCalls[variant],1);
            @synchronized(ArmyWatch.class){
                if(current==owner){
                    if(!ok)leave(owner);
                    else if(p[3]==5&&owner.phase==InMatch){
                        owner.nativeStarted=YES;
                    }
                    else if(p[3]==7)watchReady(owner);
                }
            }
        }
        return 1;
    }
}
void AGViewerTick(void *env,int variant) {
    if(!env||variant<0||variant>=6)return;
    if(atomic_load(&nativeCleanup[variant])&&!atomic_load(&snapshotCalls[variant])&&AGNativeWatchTryEnd(env,variant))
        atomic_store(&nativeCleanup[variant],false);
    if(atomic_load(&nativeCleanup[variant]))return;
    ArmyWatch *closing,*leaving;
    @synchronized(ArmyWatch.class){
        leaving=pendingLeave[variant];pendingLeave[variant]=nil;
        closing=closingWatch[variant];closingWatch[variant]=nil;
    }
    if(leaving){
        uint8_t data[12]={0x53,0x50,1,2};
        memcpy(data+4,leaving.ticket.bytes,8);
        AGViewerSend(env,variant,leaving.connection,-102,data,sizeof data);
    }
    if(closing)dispatch_async(dispatch_get_main_queue(),^{[closing close];});
    if(closing.battlefield&&!closing.switchToPB)AGLobbyWatchFinished(variant,closing.connection);
    int pb=atomic_exchange(&pendingPB[variant],0);
    if(pb)AGNativeWatchSwitch(env,pb-1);
    AGNativeWatchTick(env,variant);
    uintptr_t wait=atomic_exchange(&nativeWait[variant],0);
    if(wait)AGViewerDismissWait(variant,wait);
    if(!atomic_load(&active))return;
    @autoreleasepool {
        ArmyWatch *w;WatchAction action;uintptr_t connection;
        @synchronized(ArmyWatch.class){
            w=current;if(!w||w.variant!=variant)return;
            BOOL aux=AGNativeWatchAux(variant);
            if(w.auxiliary!=aux){
                w.auxiliary=aux;
                dispatch_async(dispatch_get_main_queue(),^{
                    [w.web evaluateJavaScript:[NSString stringWithFormat:@"watchNativeMenu(%d)",aux] completionHandler:nil];
                    ((AGWatchSurface *)w.view).passesGameTouches=aux;
                });
            }
            int angle=AGNativeWatchAngle(variant);
            if(angle>=0&&angle!=w.shownAngle){
                w.shownAngle=angle;
                dispatch_async(dispatch_get_main_queue(),^{
                    [w.web evaluateJavaScript:[NSString stringWithFormat:@"watchAngle(%d)",angle] completionHandler:nil];
                });
            }
        }
        connection=AGViewerConnection(env,variant);
        @synchronized(ArmyWatch.class){
            if(current!=w)return;
            if(connection!=w.connection){finish(w);return;}
            advanceWatch(w,now());
            if(current!=w)return;
            action=w.action;w.action=NoAction;
        }
        if(action!=Accept)return;
        uint8_t data[14]={0x53,0x50,1,1,w.room,w.area};
        memcpy(data+6,w.ticket.bytes,8);
        int ok=AGViewerSend(env,variant,connection,-102,data,sizeof data);
        @synchronized(ArmyWatch.class){if(!ok)finish(w);}
    }
}

@implementation ArmyWatch
- (void)loadView {
    UIView *view=[AGWatchSurface new];view.opaque=NO;view.backgroundColor=UIColor.clearColor;self.view=view;
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    CGRect game=AGGameRect(self.view);
    self.web.frame=game;
    ((AGWatchSurface *)self.view).gameBottom=CGRectGetMaxY(game);
}
- (void)show {
    @synchronized(ArmyWatch.class){if(current!=self)return;}
    if(!self.parentViewController){
        UIWindow *previous=visibleHost();
        if(!previous){
            if(!self.retryScheduled){
                self.retryScheduled=YES;
                dispatch_after(dispatch_time(DISPATCH_TIME_NOW,250*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
                    self.retryScheduled=NO;
                    [self show];
                });
            }
            return;
        }
        self.previous=previous;
        self.window=previous;
        if(!AGWatchMount(self,previous))return;
        ((AGWatchSurface *)self.view).gameBottom=CGRectGetMaxY(AGGameRect(self.view));
        if(!self.keypadCaptured){AGViewportWheelVisible(1);self.keypadCaptured=YES;}
    }
    if(!self.watchdog){
        __weak ArmyWatch *watch=self;
        self.watchdog=[NSTimer timerWithTimeInterval:.25 repeats:YES block:^(NSTimer *timer){[watch checkDeadline];}];
        [NSRunLoop.mainRunLoop addTimer:self.watchdog forMode:NSRunLoopCommonModes];
    }
    if(!self.web){
        NSURL *html=[[NSBundle bundleForClass:ArmyWatch.class] URLForResource:(AGNativeWatchAvailable()?@"native-watch":@"index") withExtension:@"html" subdirectory:@"viewer"];
        if(!html){[self cancel];return;}
        WKWebViewConfiguration *config=[WKWebViewConfiguration new];
        config.websiteDataStore=[WKWebsiteDataStore nonPersistentDataStore];
        [config.userContentController addScriptMessageHandler:self name:@"viewer"];
        self.web=[[WKWebView alloc] initWithFrame:CGRectZero configuration:config];self.web.navigationDelegate=self;
        self.web.opaque=NO;
        self.web.backgroundColor=UIColor.clearColor;
        self.web.scrollView.backgroundColor=UIColor.clearColor;
        self.web.scrollView.scrollEnabled=NO;
        self.web.scrollView.bounces=NO;
        self.web.scrollView.contentInsetAdjustmentBehavior=UIScrollViewContentInsetAdjustmentNever;
        [self.view addSubview:self.web];
        [self.web loadFileURL:html allowingReadAccessToURL:html.URLByDeletingLastPathComponent];
    }
    [self.view setNeedsLayout];
    [self updatePhase];
    if(self.webReady&&AGNativeWatchAvailable())
        [self.web evaluateJavaScript:[NSString stringWithFormat:@"watchVariant(%d)",self.variant+1] completionHandler:nil];
}
- (void)updatePhase {
    if(!self.webReady)return;
    WatchPhase phase;
    NSString *message;
    @synchronized(ArmyWatch.class){
        if(current!=self)return;
        phase=self.phase;
        if(AGNativeWatchAvailable()&&phase==InMatch&&!self.snapshotReceived)phase=WaitingForMatch;
        message=phase==Offered?self.question:nil;
    }
    NSData *data=[NSJSONSerialization dataWithJSONObject:@[@(phase),message?:@""] options:0 error:nil];
    NSString *arg=[[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    if(arg)[self.web evaluateJavaScript:[NSString stringWithFormat:@"setWatchPhase(...%@)",arg] completionHandler:nil];
    int angle=AGNativeWatchAngle(self.variant);
    if(phase==InMatch&&angle>=0)
        [self.web evaluateJavaScript:[NSString stringWithFormat:@"watchAngle(%d)",angle] completionHandler:nil];
}
- (void)accept {
    @synchronized(ArmyWatch.class){
        if(current!=self||self.phase!=Offered)return;
        AGNativeWatchTraceReset(self.variant);
        self.phase=WaitingForMatch;self.action=Accept;self.deadline=now()+15;
    }
    [self show];
}
- (void)cancel {@synchronized(ArmyWatch.class){if(current==self)leave(self);}}
- (void)checkDeadline {
    @synchronized(ArmyWatch.class){if(current==self)advanceWatch(self,now());}
    if(now()-self.traceSavedAt<1)return;
    self.traceSavedAt=now();
    AGWatchTrace trace;if(!AGNativeWatchTraceCopy(self.variant,&trace))return;
    uint64_t render[5]={0};AGNativeWatchTraceRenderCopy(self.variant,render);
    NSDictionary *report=@{@"build":@293,@"pb":@(self.variant+1),@"phase":@(self.phase),
        @"snapshot_ready":@(self.snapshotReceived),@"native_running":@(AGNativeWatchRunning(self.variant)),
        @"watch_active":@(AGViewerActive(self.variant)),@"still_watching":@(AGViewerStillWatching(self.variant)),
        @"render_callbacks":@(render[0]),@"render_steps":@(render[1]),@"render_completed":@(render[2]),
        @"render_failures":@(render[3]),@"canvas_updates_deferred":@(render[4]),
        @"scene_entries":@(trace.frames),@"received_packets":@(trace.packets),
        @"last_command":@(trace.command),@"last_snapshot_operation":@(trace.operation),
        @"wait_count":@(trace.waits),@"wait_kind":@(trace.waitKind),@"wait_actor":@(trace.waitActor),
        @"wait_stage":@(trace.waitStage),@"wait_expirations":@(trace.expirations),
        @"scene_exceptions":@(trace.exceptions),@"first_exception":[NSString stringWithUTF8String:trace.exception]?:@""};
    NSData *data=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil];
    NSString *directory=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    if(data&&directory)[data writeToFile:[directory stringByAppendingPathComponent:@"Watch293-diagnostic.json"] atomically:YES];
}
- (void)close {
    [self.watchdog invalidate];self.watchdog=nil;
    [self.web.configuration.userContentController removeScriptMessageHandlerForName:@"viewer"];
    [self.web stopLoading];self.web.navigationDelegate=nil;
    if(self.keypadCaptured){AGViewportWheelVisible(0);self.keypadCaptured=NO;}
    AGWatchUnmount(self);
    self.window=nil;self.previous=nil;
}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message {
    if(message.webView!=self.web||!message.frameInfo.isMainFrame)return;
    if([message.body isEqual:@"ready"]){
        self.webReady=YES;[self updatePhase];[self flush];
        if(AGNativeWatchAvailable())[self.web evaluateJavaScript:[NSString stringWithFormat:@"watchVariant(%d)",self.variant+1] completionHandler:nil];
    }
    else if([message.body isEqual:@"live"]){
        @synchronized(ArmyWatch.class){if(current==self&&self.phase==InMatch&&self.snapshotReceived&&!self.endReceived)self.deadline=0;}
    }else if([message.body isEqual:@"ended"]){
        @synchronized(ArmyWatch.class){if(current==self&&self.endReceived)finish(self);}
    }
    else if([message.body isEqual:@"accept"])[self accept];
    else if([message.body isEqual:@"decline"]||[message.body isEqual:@"leave"]||[message.body isEqual:@"failed"])[self cancel];
    else if(AGNativeWatchAvailable()){
        @synchronized(ArmyWatch.class){
            if(current!=self||self.phase!=InMatch||!self.snapshotReceived)return;
            if([message.body isEqual:@"camera"]){
                updateCamera(self);
            }else if([message.body isEqual:@"menuOpen"]||[message.body isEqual:@"menuClosed"]){
                self.menuVisible=[message.body isEqual:@"menuOpen"];
                if(self.menuVisible)AGNativeWatchClearCameraKeys(self.variant);
            }else if([message.body isKindOfClass:NSArray.class]&&[message.body count]==2&&[message.body[1] isKindOfClass:NSNumber.class]){
                int option=[message.body[1] intValue];
                if([message.body[0] isEqual:@"option"])AGNativeWatchOption(self.variant,option);
                if([message.body[0] isEqual:@"nudge"]&&!self.menuVisible&&!self.auxiliary&&option>=-4&&option<=-1)
                    AGNativeWatchNudgeCamera(self.variant,option);
                if([message.body[0] isEqual:@"pb"]&&option>0&&option<=6&&option!=self.variant+1){
                    self.switchToPB=option;
                    leave(self);
                }
            }else if([message.body isKindOfClass:NSArray.class]&&[message.body count]==3&&
                      [message.body[0] isEqual:@"key"]&&[message.body[1] isKindOfClass:NSNumber.class]&&
                      [message.body[2] isKindOfClass:NSNumber.class]){
                int kind=[message.body[1] intValue],key=[message.body[2] intValue];
                if((kind==1||(kind==0&&AGNativeWatchFree(self.variant)&&!self.menuVisible&&!self.auxiliary))&&key>=-4&&key<=-1)
                    AGNativeWatchCamera(self.variant,kind,key);
            }
        }
    }
}
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView {[self cancel];}
- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)nav withError:(NSError *)error {[self cancel];}
- (void)flush {
    if(AGNativeWatchAvailable()||!self.webReady||self.delivering)return;
    NSMutableArray *batch=[NSMutableArray array];
    @synchronized(ArmyWatch.class){
        if(current!=self||self.phase!=InMatch)return;
        NSUInteger count=MIN(24,self.pending.count);
        for(NSUInteger i=0;i<count;i++){
            NSArray *row=self.pending[i];NSData *bytes=row[1];
            [batch addObject:@[row[0],[bytes base64EncodedStringWithOptions:0]]];
            self.pendingBytes-=bytes.length;
        }
        [self.pending removeObjectsInRange:NSMakeRange(0,count)];
    }
    if(!batch.count)return;
    NSData *json=[NSJSONSerialization dataWithJSONObject:batch options:0 error:nil];
    NSString *arg=[[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding];
    self.delivering=YES;
    [self.web evaluateJavaScript:[NSString stringWithFormat:@"window.receiveArmyFrames(%@)",arg] completionHandler:^(id result,NSError *error){
        self.delivering=NO;if(error){[self cancel];return;}[self flush];
    }];
}
@end


