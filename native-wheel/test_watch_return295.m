/* Production Objective-C receive/tick/close flow on iOS Simulator.
   Native battle execution and socket transport are explicit boundaries. */
#ifndef WATCH_PRODUCTION
#define WATCH_PRODUCTION "Spectator.m"
#endif
#import WATCH_PRODUCTION
#include <stdlib.h>
#ifdef WATCH_WITH_LOBBY
#define AG_WHEEL_PREVIEW 1
#import "Lobby.m"
#import "GameViewport.m"
#endif

static uintptr_t session295=0x123456;
static int running295[6],cleanupBlocked295,switches295,board295,keypad295,failRoom295;
static NSMutableArray *sent295;
static void *env295=(void *)0x1000;
static int roomStatus295=14;
int AGNativeWatchAvailable(void){return 1;}
int AGNativeWatchFree(int v){return 0;}
int AGNativeWatchRunning(int v){return running295[v];}
int AGNativeWatchAngle(int v){return -1;}
int AGNativeWatchPacket(void *e,int v,const uint8_t *p,size_t n){if(n>=4&&p[3]==7)running295[v]=1;return 1;}
int AGNativeWatchReplay(void *e,int v,int c,const uint8_t *p,size_t n){return 1;}
int AGNativeWatchFinishSnapshot(void *e,int v){running295[v]=1;return 1;}
int AGNativeWatchTryFinishSnapshot(void *e,int v){return AGNativeWatchFinishSnapshot(e,v);}
void AGNativeWatchObserve(int v,int c,const uint8_t *p,size_t n){}
void AGNativeWatchOption(int v,int o){}
int AGNativeWatchAux(int v){return 0;}
void AGNativeWatchSwitch(void *e,int v){switches295++;}
void AGNativeWatchEnd(void *e,int v){running295[v]=0;}
int AGNativeWatchTryEnd(void *e,int v){if(cleanupBlocked295)return 0;running295[v]=0;return 1;}
int AGNativeWatchRoomStatus(void *e,int v){return roomStatus295;}
void AGNativeWatchCamera(int v,int k,int c){}
int AGNativeWatchToggleCamera(int v){return 0;}
void AGNativeWatchClearCameraKeys(int v){}
void AGNativeWatchNudgeCamera(int v,int c){}
void AGNativeWatchTick(void *e,int v){}
uintptr_t AGViewerConnection(void *e,int v){return session295;}
uintptr_t AGViewerWaitToken(int v){return 0;}
void AGViewerDismissWait(int v,uintptr_t t){}
int AGViewerSend(void *e,int v,uintptr_t expected,int command,const uint8_t *p,size_t n){
    NSCAssert(e==env295,@"Wrong JNI environment");
    if(expected!=session295)return 0;
    if(command==7&&failRoom295){failRoom295--;return 0;}
    [sent295 addObject:@{@"cmd":@(command),@"body":[NSData dataWithBytes:p length:n]}];
    return 1;
}
#ifndef WATCH_WITH_LOBBY
void AGLobbyWatchFinished(int v,uintptr_t c){board295++;}
void AGViewportWheelVisible(int visible){keypad295+=visible?1:-1;NSCAssert(keypad295>=0,@"Unbalanced keypad ownership");}
CGRect AGGameRect(UIView *view){CGRect r=view.bounds;r.size.height*=.72;return r;}
#else
int AGWheelGuard(void *e,int (*fn)(void *,void *),void *j,void *entry){return 0;}
int AGLobbyReadAccount(void *e,int v,AGLobbyAccount *a){return 0;}
int AGLobbySend(void *e,int v,uintptr_t c,int command,const uint8_t *p,size_t n){return 1;}
int AGAuraRank(int v,uintptr_t c,uint32_t id,unsigned hero){return 0;}
#endif
void AGNativeWatchTraceReset(int v){}
void AGNativeWatchTracePacket(int v,int c,int o){}
int AGNativeWatchTraceCopy(int v,AGWatchTrace *o){memset(o,0,sizeof *o);return 1;}
int AGNativeWatchTraceRenderCopy(int v,uint64_t o[5]){memset(o,0,40);return 1;}

static void pump295(double seconds){
    NSTimeInterval until=NSProcessInfo.processInfo.systemUptime+seconds;
    do{[NSThread sleepForTimeInterval:.01];}
    while(NSProcessInfo.processInfo.systemUptime<until);
}
static void ui295(dispatch_block_t block){dispatch_sync(dispatch_get_main_queue(),block);}
static int receive295(int v,int command,NSData *body){
    NSMutableData *array=[NSMutableData dataWithLength:0x14+body.length];
    *(int *)((uint8_t *)array.mutableBytes+0x10)=(int)body.length;
    memcpy((uint8_t *)array.mutableBytes+0x14,body.bytes,body.length);
    uint8_t input[0x28]={0},message[0x40]={0};
    *(void **)(input+0x10)=array.mutableBytes;*(int *)(input+0x18)=(int)body.length;
    *(void **)(message+0x20)=input;*(int8_t *)(message+0x30)=command;
    return AGViewerReceive(env295,message,v);
}
static NSData *end295(ArmyWatch *w){
    uint8_t p[12]={0x53,0x50,1,6};memcpy(p+4,w.ticket.bytes,8);
    return [NSData dataWithBytes:p length:12];
}
static ArmyWatch *offer295(int v){
    uint8_t p[17]={0x53,0x50,1,0,0,3,1,2,3,4,5,6,7,8,0,1,'?'};
    NSCAssert(receive295(v,-102,[NSData dataWithBytes:p length:sizeof p])==1,@"Offer not consumed");
    __block ArmyWatch *w;__block BOOL mounted;
    ui295(^{w=current;mounted=w&&w.parentViewController&&w.view.superview;});
    NSCAssert(w&&w.phase==Offered&&mounted,@"Real overlay did not mount");
    return w;
}
static ArmyWatch *start295(int v){
    ArmyWatch *w=offer295(v);ui295(^{[w accept];});AGViewerTick(env295,v);
    uint8_t p[21]={0x53,0x50,1,3,0,3};memcpy(p+6,w.ticket.bytes,8);
    p[15]=3;p[16]=0xe8;p[17]=3;p[18]=0x20;
    receive295(v,-102,[NSData dataWithBytes:p length:21]);
    uint8_t roster[42]={0};receive295(v,8,[NSData dataWithBytes:roster length:42]);
    uint8_t snapshot[31]={0x53,0x50,1,5,30,0,100,0,100,0,0,0,0,0,0,3,0xe8};
    memset(snapshot+17,255,14);
    receive295(v,-102,[NSData dataWithBytes:snapshot length:31]);
    uint8_t ready[5]={0x53,0x50,1,7,30};receive295(v,-102,[NSData dataWithBytes:ready length:5]);
    pump295(.02);
    NSCAssert(w.phase==InMatch&&w.snapshotReceived&&AGViewerStillWatching(v),@"Watch never became ready");
    [sent295 removeAllObjects];return w;
}
static NSUInteger roomRequests295(void){
    NSUInteger n=0;
    for(NSDictionary *event in sent295)if([event[@"cmd"] intValue]==7){
        NSData *body=event[@"body"];NSCAssert(body.length==1&&((const uint8_t *)body.bytes)[0]==0,@"Requested wrong room");n++;
    }
    return n;
}
static void detached295(ArmyWatch *w,int v){
    pump295(.04);
    __block BOOL removed;ui295(^{removed=!w.parentViewController&&!w.view.superview;});
    NSCAssert(removed,@"Closed watch still intercepts native touches");
    NSCAssert(!AGViewerActive(v)&&!AGViewerStillWatching(v)&&!AGNativeWatchRunning(v),@"Watch flags still block normal play");
    NSCAssert(AGViewerInput(v,0,-6)==0&&AGViewerInput(v,1,-6)==0&&AGViewerInput(v,1,'4')==0&&AGViewerInput(v,2,0)==0,@"Room keys/touches are still consumed");
    NSCAssert(keypad295==0,@"Watch still owns native keypad");
}

#ifdef WATCH_WITH_LOBBY
static void recovery296(void){
    ArmyWatch *w=start295(0);ui295(^{[w cancel];});roomStatus295=0;
    AGViewerTick(env295,0);detached295(w,0);
    NSCAssert(roomRequests295()==1,@"Missing initial room0 request");
    pump295(1.05);AGViewerTick(env295,0);
    NSCAssert(roomRequests295()==2,@"Socket enqueue was mistaken for a room reply");
    const uint8_t empty[]={0};receive295(0,7,[NSData dataWithBytes:empty length:1]);
    pump295(1.05);AGViewerTick(env295,0);
    NSCAssert(roomRequests295()==3&&!w.roomReplyReceived,@"Empty area reply stopped recovery");
    const uint8_t full[]={0,0,0,4,0,0,0,0,0,0,0,1,'A',0};
    receive295(0,7,[NSData dataWithBytes:full length:sizeof full]);roomStatus295=14;
    pump295(1.05);AGViewerTick(env295,0);
    NSCAssert(roomRequests295()==3&&w.roomReturnComplete&&!pendingRoomReturn[0],@"Populated native area screen did not acknowledge return");
    w=start295(0);ui295(^{[w cancel];});AGViewerTick(env295,0);detached295(w,0);
    roomStatus295=-1;pump295(1.05);AGViewerTick(env295,0);
    NSCAssert(roomRequests295()==1&&!pendingRoomReturn[0],@"Navigation away from room0 did not cancel retries");
    roomStatus295=14;
}
static id js296(WKWebView *web,NSString *script){
    __block id result;__block BOOL done=NO;
    ui295(^{[web evaluateJavaScript:script completionHandler:^(id value,NSError *error){result=value;done=YES;}];});
    for(int i=0;i<200&&!done;i++)pump295(.01);
    NSCAssert(done,@"Lobby JavaScript stopped responding");return result;
}
static void battlefield296(UIWindow *host){
    for(int v=0;v<6;v++)for(int automatic=0;automatic<2;automatic++){
        __block AGLobby *panel;
        ui295(^{
            connections[v]=session295;panel=[AGLobby new];panel.variant=v;panel.connection=session295;panel.tab=AGLobbyField;
            AGLobbyAccount account={.canvasWidth=450};panel.account=account;
            [panel open];
        });
        BOOL ready=NO;
        for(int i=0;i<100&&!ready;i++){
            ready=[js296(panel.web,@"typeof lobbyWatchReturned === 'function'") isEqual:@YES];
            if(!ready)pump295(.03);
        }
        NSCAssert(ready,@"Real battlefield page failed to load");
        ui295(^{
            int samples=v==0&&!automatic?40:1;
            for(int i=0;i<samples;i++)AGSaveProfileDiagnostic(panel,@{@"requested_id":@41,@"hero":@9,@"serial":@(i+1),@"item_ids":@[@56,@54,@55,@57,@58,@2999],@"icon_sources":@[@1,@1,@2,@2,@3,@0],@"flat":@[@[@115,@181,@95,@96,@91]],@"PRIVATE_ACCOUNT_NAME":@"DO_NOT_EXPORT_PNG_OR_ACCOUNT_TEXT"});
        });
        dispatch_sync(AGProfileDiagnosticQueue(),^{});
        NSString *profilePath=[NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject stringByAppendingPathComponent:@"Profile1-diagnostic.json"];
        NSData *profileBytes=[NSData dataWithContentsOfFile:profilePath];
        NSDictionary *profileReport=profileBytes?[NSJSONSerialization JSONObjectWithData:profileBytes options:0 error:nil]:nil;
        NSCAssert([profileReport[@"latest"][@"pb"] intValue]==v+1&&[profileReport[@"latest"][@"profile"][@"hero"] intValue]==9,@"Profile diagnostic lost the selected PB/hero");
        NSCAssert([profileReport[@"history"] count]<=32&&[profileReport[@"latest"][@"profile"][@"item_ids"] count]==6,@"Profile diagnostic is unbounded or lost slot identity");
        NSCAssert(![[[NSString alloc]initWithData:profileBytes encoding:NSUTF8StringEncoding] containsString:@"DO_NOT_EXPORT"],@"Profile diagnostic exported account text or payloads");
        js296(panel.web,@"window.returned296=0;const saved296=lobbyWatchReturned;window.lobbyWatchReturned=()=>{returned296++;saved296();}");
        uint32_t serial=12345;panel.watchSerial=serial;
        uint8_t ack[9]={'C','T','4','6',6};memcpy(ack+5,&serial,4);
        uint8_t input[0x28]={0},message[0x40]={0},array[0x14+9]={0};
        *(int *)(array+0x10)=9;memcpy(array+0x14,ack,9);
        *(void **)(input+0x10)=array;*(int *)(input+0x18)=9;
        *(void **)(message+0x20)=input;*(int8_t *)(message+0x30)=-120;
        NSCAssert(AGLobbyReceive(env295,message,v)==1,@"Battlefield watch acknowledgement rejected");
        pump295(.04);
        NSCAssert(panel.watching&&panel.overlay.hidden&&!AGLobbyOpened(v),@"Battlefield did not suspend its input before watching");
        ArmyWatch *w=start295(v);
        if(automatic)receive295(v,-102,end295(w));else ui295(^{[w cancel];});
        AGViewerTick(env295,v);detached295(w,v);
        __block BOOL visible;ui295(^{visible=panel.overlay.isKeyWindow&&!panel.overlay.hidden;});
        NSCAssert(visible&&!panel.watching&&AGLobbyOpened(v),@"Battlefield window/input did not return");
        NSCAssert(roomRequests295()==0,@"Battlefield exit incorrectly requested room0");
        NSCAssert([js296(panel.web,@"returned296") intValue]==1,@"Battlefield page return callback missed or duplicated");
        ui295(^{[panel close];});pump295(.02);
        NSCAssert(!AGLobbyOpened(v)&&!AGLobbyInput(v,0,-7,0),@"Closed battlefield still consumes keys");
        __block BOOL restored;ui295(^{restored=host.isKeyWindow;});
        NSCAssert(restored,@"Battlefield close did not restore the original game window");
    }
}
#endif

@interface Return295App : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@end
@implementation Return295App
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
    self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];
    self.window.rootViewController=[UIViewController new];[self.window makeKeyAndVisible];
    // Keep the main queue free to execute production's asynchronous show/close.
    // Receive and native ticks normally run off the main queue in the real game.
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
        BOOL passed=YES;NSString *reason=@"";sent295=[NSMutableArray array];
        @try{
            for(int v=0;v<6;v++){
                // Manual leave: cleanup must complete before SP2 then room0.
                ArmyWatch *w=start295(v);AGViewerInput(v,0,'4');ui295(^{[w cancel];});cleanupBlocked295=1;
                AGViewerTick(env295,v);NSCAssert(sent295.count==0,@"Sent return before cleanup");
                cleanupBlocked295=0;AGViewerTick(env295,v);
                NSCAssert(sent295.count==2&&[sent295[0][@"cmd"] intValue]==-102&&roomRequests295()==1,@"Manual leave did not send SP2 then room0");
                NSCAssert(((const uint8_t *)[sent295[0][@"body"] bytes])[3]==2,@"Wrong leave operation");
                detached295(w,v);AGViewerTick(env295,v);NSCAssert(roomRequests295()==1,@"Duplicate room refresh");

                // Server finish uses the same room0 return, without SP2.
                w=start295(v);NSData *end=end295(w);receive295(v,-102,end);AGViewerTick(env295,v);
                NSCAssert(sent295.count==1&&roomRequests295()==1,@"SP6 did not request full room0 areas");
                detached295(w,v);receive295(v,-102,end);AGViewerTick(env295,v);
                NSCAssert(roomRequests295()==1,@"Duplicate SP6 repeated room refresh");

                // Offers declined before joining never rejoin a room.
                [sent295 removeAllObjects];w=offer295(v);ui295(^{[w cancel];});AGViewerTick(env295,v);detached295(w,v);
                NSCAssert(sent295.count==0,@"Decline sent a room request");
                w=offer295(v);ui295(^{[w accept];[w cancel];});AGViewerTick(env295,v);detached295(w,v);
                NSCAssert(sent295.count==0,@"Unsent accept caused a room request");

                // No old-session room request may reach a replacement login.
                w=start295(v);receive295(v,-102,end295(w));session295++;AGViewerTick(env295,v);detached295(w,v);
                NSCAssert(sent295.count==0,@"Old session returned a new login to room0");

                // A PB switch and custom battlefield keep their own destination.
                w=start295(v);w.switchToPB=(v+1)%6+1;ui295(^{[w cancel];});AGViewerTick(env295,v);detached295(w,v);
                NSCAssert(roomRequests295()==0,@"PB switch incorrectly joined old room");
                AGViewerExpectBattlefield(v,session295);w=start295(v);receive295(v,-102,end295(w));AGViewerTick(env295,v);detached295(w,v);
                NSCAssert(roomRequests295()==0,@"Battlefield return incorrectly joined room0");
            }
            // A transient native send failure retries once the tick can send.
            ArmyWatch *w=start295(0);receive295(0,-102,end295(w));failRoom295=1;
            AGViewerTick(env295,0);detached295(w,0);NSCAssert(roomRequests295()==0,@"Failed send was marked successful");
            AGViewerTick(env295,0);NSCAssert(roomRequests295()==0,@"Return retry spins every frame");
            pump295(1.05);AGViewerTick(env295,0);NSCAssert(roomRequests295()==1,@"Room refresh was lost after a transient send failure");
            NSCAssert(switches295==6,@"PB return destinations changed");
#ifndef WATCH_WITH_LOBBY
            NSCAssert(board295==6,@"Battlefield callback count changed");
#else
            recovery296();battlefield296(self.window);
#endif
            __block BOOL rootRestored;ui295(^{rootRestored=self.window.isKeyWindow&&self.window.rootViewController.childViewControllers.count==0;});
            NSCAssert(rootRestored,@"Root/window state was not restored");
            reason=@"Production receive/tick/close: six PBs, SP6/manual SP2 -> room0, cleanup ordering, duplicate protection, cancel/session/PB/battlefield safety, retry and native input/touch restoration";
        }@catch(NSException *error){passed=NO;reason=error.reason?:error.name;}
        NSDictionary *report=@{@"passed":@(passed),@"reason":reason};
        NSString *docs=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
#ifdef WATCH_WITH_LOBBY
        NSString *filename=@"return296-result.json";
#else
        NSString *filename=@"return295-result.json";
#endif
        [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil] writeToFile:[docs stringByAppendingPathComponent:filename] atomically:YES];
        exit(passed?0:1);
    });
    return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(Return295App.class));}}

