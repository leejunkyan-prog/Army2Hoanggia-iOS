#import <UIKit/UIKit.h>
#import <WebKit/WebKit.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <string.h>
#include <math.h>
#include "ProfileIcons.h"
#include "Lobby.h"
#include "Spectator.h"
#include "Aura.h"
#import "GameViewport.h"

@interface AGLobby : UIViewController <WKScriptMessageHandler,WKNavigationDelegate>
@property(nonatomic,strong) UIWindow *overlay;
@property(nonatomic,weak) UIWindow *host;
@property(nonatomic,strong) WKWebView *web;
@property(nonatomic) uintptr_t connection;
@property(nonatomic) int variant;
@property(nonatomic) int tab;
@property(nonatomic) BOOL loaded;
@property(nonatomic) AGLobbyAccount account;
@property(nonatomic) uint32_t firstSerial;
@property(nonatomic) int command;
@property(nonatomic) uint32_t watchSerial;
@property(nonatomic) uint32_t challengeSerial;
@property(nonatomic) int fieldResult;
@property(nonatomic) BOOL closing;
@property(nonatomic) BOOL watching;
@property(nonatomic) BOOL requestedGearAtlas;
@property(nonatomic,strong) NSDictionary *profileIconRequest;
@property(nonatomic) NSTimeInterval watchDeadline;
@property(nonatomic,strong) NSData *outgoing;
@property(nonatomic,strong) NSMutableArray *profileHistory;
- (void)open;
- (void)close;
@end

static atomic_bool opened[6];
static unsigned char held[6][256],pointer[6];
static BOOL opening;
static uintptr_t connections[6];
static uintptr_t battlefield[6];
static uintptr_t returnToBoard[6];
static int fieldResult[6];
static uint32_t nextFieldSerial;
static AGLobby *activePanel;
static NSData *gearAtlas[6];
static uintptr_t atlasConnection[6];
static uintptr_t atlasRequest[6];
enum { NoFieldResult = 256 };

static dispatch_queue_t AGProfileDiagnosticQueue(void){
    static dispatch_queue_t queue;static dispatch_once_t once;
    dispatch_once(&once,^{queue=dispatch_queue_create("army2.profile.diagnostic",DISPATCH_QUEUE_SERIAL);});return queue;
}
/* Only bounded numbers/arrays. Names, chat, credentials, PNG bytes and packet
   payloads cannot enter this report even if an unexpected web field arrives. */
static id AGProfileNumber(id value,int depth){
    if([value isKindOfClass:NSNumber.class]){
        double n=[value doubleValue];long long i=[value longLongValue];
        return isfinite(n)&&n==(double)i&&i>=INT32_MIN&&i<=INT32_MAX?@(i):nil;
    }
    if(depth<2&&[value isKindOfClass:NSArray.class]&&[value count]<=6){
        NSMutableArray *copy=[NSMutableArray array];
        for(id part in value){id n=AGProfileNumber(part,depth+1);if(!n)return nil;[copy addObject:n];}
        return [copy copy];
    }
    return nil;
}
static void AGSaveProfileDiagnostic(AGLobby *panel,NSDictionary *input){
    if(panel.tab!=AGLobbyField||panel.closing)return;
    NSMutableDictionary *fields=[NSMutableDictionary dictionary];
    for(NSString *key in @[@"requested_id",@"rank",@"serial",@"hero",@"level",@"abilities",@"item_ids",@"upgrades",@"tiers",
        @"has_details",@"flat",@"percent",@"gem_counts",@"icon_bytes",@"icon_sources",@"catalog_frames",@"atlas_width",@"atlas_height",@"native_icon_ids",@"native_icon_status"]){
        id n=AGProfileNumber(input[key],0);if(n)fields[key]=n;
    }
    if(!fields[@"requested_id"]||[fields[@"requested_id"] intValue]<1||!fields[@"hero"]||[fields[@"hero"] intValue]<0||[fields[@"hero"] intValue]>9)return;
    NSString *stamp=[[NSISO8601DateFormatter new] stringFromDate:NSDate.date];
    NSDictionary *sample=@{@"at":stamp,@"pb":@(panel.variant+1),@"profile":[fields copy]};
    if(!panel.profileHistory)panel.profileHistory=[NSMutableArray array];
    [panel.profileHistory addObject:sample];while(panel.profileHistory.count>32)[panel.profileHistory removeObjectAtIndex:0];
    int build=[NSBundle.mainBundle.infoDictionary[@"CFBundleVersion"] intValue];
    NSDictionary *report=@{@"build":@(build),@"created_at":stamp,@"latest":sample,@"history":[panel.profileHistory copy],
        @"icon_source_legend":@{@"0":@"server_icon_unavailable",@"1":@"profile_server_png",@"2":@"live_server_catalog",@"3":@"image_loading",@"4":@"invalid_profile_png",@"5":@"native_server_catalog_image"}};
    NSData *data=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil];if(!data||data.length>262144)return;
    NSString *directory=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    NSString *path=[directory stringByAppendingPathComponent:[NSString stringWithFormat:@"Profile%d-diagnostic.json",build]];
    dispatch_async(AGProfileDiagnosticQueue(),^{[data writeToFile:path atomically:YES];});
}

void AGLobbyWatchFinished(int v,uintptr_t connection){
    AGLobby *panel;
    @synchronized(AGLobby.class){
        panel=activePanel;
        if(!panel.watching||panel.closing||panel.variant!=v||panel.connection!=connection)return;
        panel.watching=NO;panel.watchDeadline=0;
        atomic_store(&opened[v],1);
    }
    dispatch_async(dispatch_get_main_queue(),^{
        if(!panel.overlay||panel.closing)return;
        AGViewportWheelVisible(1);
        [panel.overlay makeKeyAndVisible];
        [panel.web evaluateJavaScript:@"lobbyWatchReturned()" completionHandler:nil];
    });
}

static NSString *eventAuras(NSData *body,int variant,uintptr_t connection){
    const uint8_t *p=body.bytes;
    size_t length=body.length;
    if(length<4)return @"[]";
    size_t pos=4+((p[2]<<8)|p[3]);
    NSMutableArray *codes=[NSMutableArray arrayWithCapacity:10];
    while(pos<length&&codes.count<10){
        if(length-pos<6)return @"[]";
        uint32_t id=(uint32_t)p[pos]<<24|(uint32_t)p[pos+1]<<16|(uint32_t)p[pos+2]<<8|p[pos+3];
        pos+=6+((p[pos+4]<<8)|p[pos+5]);
        if(pos>length||length-pos<25)return @"[]";
        [codes addObject:[NSString stringWithFormat:@"%d",AGAuraRank(variant,connection,id,p[pos])]];
        pos+=23;
        pos+=2+((p[pos]<<8)|p[pos+1]);
    }
    if(pos!=length)return @"[]";
    return [NSString stringWithFormat:@"[%@]",[codes componentsJoinedByString:@","]];
}

int AGLobbyOpened(int variant){return variant>=0&&variant<6?atomic_load(&opened[variant]):0;}
int AGLobbyInput(int variant,int kind,int code,int b){
    (void)b;
    if(variant<0||variant>=6)return 0;
    AGLobby *active;
    BOOL consumed;
    unsigned index=(unsigned)code+128;
    @synchronized(AGLobby.class){
        active=activePanel;
        consumed=atomic_load(&opened[variant]);
        if(kind==1&&index<256&&held[variant][index]){held[variant][index]=0;consumed=YES;}
        if(kind==4&&pointer[variant]){pointer[variant]=0;consumed=YES;}
        if(consumed&&kind==0&&index<256)held[variant][index]=1;
        if(consumed&&kind==2)pointer[variant]=1;
    }
    if(consumed&&kind==0)dispatch_async(dispatch_get_main_queue(),^{
        if(!active||active.variant!=variant||!active.web)return;
        BOOL back=code==-7||code==-22||code==-11||code==27||code==35||code=='R'||code=='r';
        NSString *script=[NSString stringWithFormat:@"typeof lobbyKey === 'function' && (lobbyKey(%d),true)",code];
        [active.web evaluateJavaScript:script completionHandler:^(id value,NSError *error){
            if(back&&(error||![value isEqual:@YES]))[active close];
        }];
    });
    return consumed;
}

static void openLobby(void *env,int variant,int tab,int outcome){
    if(!env||variant<0||variant>=6||tab<AGLobbyField||tab>AGLobbyEvent)return;
    uintptr_t connection=AGViewerConnection(env,variant);
    if(!connection)return;
    uint32_t serial=0;
    @synchronized(AGLobby.class){
        if(opening||activePanel)return;
        opening=YES;
        connections[variant]=connection;
        atomic_store(&opened[variant],1);
        if(tab==AGLobbyField){
            serial=nextFieldSerial;
            nextFieldSerial=(nextFieldSerial+100000)%2100000000;
        }
    }
    AGLobbyAccount account={.character=-1,.xu=-1,.luong=-1};
    AGLobbyReadAccount(env,variant,&account);
    dispatch_async(dispatch_get_main_queue(),^{
        AGLobby *lobby=[AGLobby new];
        lobby.variant=variant;lobby.connection=connection;lobby.tab=tab;
        lobby.account=account;lobby.firstSerial=serial;lobby.fieldResult=outcome;
        [lobby open];
    });
}

__attribute__((visibility("default"))) void AGLobbyOpenNative(void *env,int variant,int tab){
    openLobby(env,variant,tab,NoFieldResult);
}

// The game thread owns the connection. UIKit enqueues requests against it.
static NSString *AGProfileIconPNG(AGProfileIcon *icon){
    if(!icon->rgba||icon->width<1||icon->height<1)return @"";
    CGColorSpaceRef space=CGColorSpaceCreateDeviceRGB();
    CGDataProviderRef provider=CGDataProviderCreateWithData(NULL,icon->rgba,(size_t)icon->width*icon->height*4,NULL);
    CGImageRef image=CGImageCreate(icon->width,icon->height,8,32,icon->width*4,space,kCGImageAlphaLast|kCGBitmapByteOrderDefault,provider,NULL,NO,kCGRenderingIntentDefault);
    NSData *png=image?UIImagePNGRepresentation([UIImage imageWithCGImage:image]):nil;
    if(image)CGImageRelease(image);CGDataProviderRelease(provider);CGColorSpaceRelease(space);
    return png.length<65536?[png base64EncodedStringWithOptions:0]?:@"":@"";
}
static void AGLoadProfileIcons(void *env,AGLobby *panel,NSDictionary *request){
    if(!request)return;
    NSMutableArray *png=[NSMutableArray array],*statuses=[NSMutableArray array],*icons=[NSMutableArray array];
    NSArray *ids=request[@"ids"];int hero=[request[@"hero"] intValue];
    for(int slot=0;slot<6;slot++){
        AGProfileIcon image={.status=1,.iconID=-1};
        if([ids[slot] intValue]>=0)AGProfileIconRead(env,panel.variant,hero,slot,[ids[slot] intValue],&image);
        [png addObject:AGProfileIconPNG(&image)];[statuses addObject:@(image.status)];[icons addObject:@(image.iconID)];free(image.rgba);
    }
    NSMutableDictionary *reply=[request mutableCopy];reply[@"png"]=png;reply[@"status"]=statuses;reply[@"icon_ids"]=icons;
    NSData *data=[NSJSONSerialization dataWithJSONObject:reply options:0 error:nil];if(!data)return;
    NSString *script=[NSString stringWithFormat:@"lobbyNativeProfileIcons(%@)",[[NSString alloc]initWithData:data encoding:NSUTF8StringEncoding]];
    dispatch_async(dispatch_get_main_queue(),^{if(activePanel==panel&&!panel.closing&&!panel.watching)[panel.web evaluateJavaScript:script completionHandler:nil];});
}
void AGLobbyTick(void *env,int v,uintptr_t connection){
    AGLobby *active;NSData *body;int cmd=0,outcome=NoFieldResult;
    BOOL reopen=NO,requestAtlas=NO;NSDictionary *profileIcons;
    @synchronized(AGLobby.class){
        connections[v]=connection;
        if(atlasConnection[v]!=connection){atlasConnection[v]=0;gearAtlas[v]=nil;}
        if(atlasRequest[v]!=connection)atlasRequest[v]=0;
        if(battlefield[v]!=connection)battlefield[v]=0;
        if(returnToBoard[v]!=connection)returnToBoard[v]=0;
        active=activePanel;
        if(!active&&!opening&&returnToBoard[v]){
            reopen=YES;
            outcome=fieldResult[v];
            returnToBoard[v]=0;
        }
        if(active&&active.variant==v&&!active.closing&&active.connection!=connection){
            active.closing=YES;
            dispatch_async(dispatch_get_main_queue(),^{[active close];});
            return;
        }
        if(active.watching&&active.variant==v){
            if(active.watchDeadline<NSProcessInfo.processInfo.systemUptime&&!AGViewerActive(v))
                AGLobbyWatchFinished(v,connection);
            return;
        }
        if(active&&active.variant==v&&!active.closing){
            body=active.outgoing;cmd=active.command;active.outgoing=nil;
            profileIcons=active.profileIconRequest;active.profileIconRequest=nil;
            if(!body&&active.loaded&&active.tab==AGLobbyField&&!active.requestedGearAtlas&&atlasConnection[v]!=connection){
                active.requestedGearAtlas=YES;
                if(!atlasRequest[v]){atlasRequest[v]=connection;requestAtlas=YES;}
            }
        }
    }
    AGLoadProfileIcons(env,active,profileIcons);
    if(reopen)openLobby(env,v,AGLobbyField,outcome);
    if(requestAtlas){
        const uint8_t package[]={4,255};
        if(!AGLobbySend(env,v,connection,90,package,sizeof package)){
            @synchronized(AGLobby.class){if(atlasRequest[v]==connection)atlasRequest[v]=0;}
        }
    }
    if(body && !AGLobbySend(env,v,connection,cmd,body.bytes,body.length)){
        dispatch_async(dispatch_get_main_queue(),^{
            if(cmd==-120){
                [active.web evaluateJavaScript:@"lobbyRequestFailed()" completionHandler:nil];
            }else [active close];
        });
    }else if(body&&cmd==5){
        dispatch_async(dispatch_get_main_queue(),^{if(active.web)[active.web evaluateJavaScript:@"lobbyMessageSent()" completionHandler:nil];});
    }
}

int AGLobbyReceive(void *env,void *message,int v){
    if(!env||!message||v<0||v>=6)return 0;
    int cmd=*(int8_t *)((uint8_t *)message+0x30);
    if(cmd!=-120&&cmd!=-121&&cmd!=-14&&cmd!=105&&cmd!=90)return 0;
    AGLobby *active;
    uintptr_t fight,request;
    @synchronized(AGLobby.class){active=activePanel;fight=battlefield[v];request=atlasRequest[v];}
    if(cmd==105&&(!active||active.variant!=v||active.tab!=AGLobbyMarket))return 0;
    uintptr_t connection=cmd==90?request:active&&active.variant==v?active.connection:fight;
    if(!connection || connection!=AGViewerConnection(env,v))return 0;
    uint8_t *in=*(uint8_t **)((uint8_t *)message+0x20);
    if(!in)return cmd!=105&&cmd!=90;
    uint8_t *array=*(uint8_t **)(in+0x10);
    if(!array)return cmd!=105&&cmd!=90;
    int count=*(int *)(in+0x18),pos=*(int *)(in+0x20);
    if(pos<0||count<=pos||count>*(int *)(array+0x10)||count-pos>(cmd==90?2000000:65535))return cmd!=105&&cmd!=90;
    const uint8_t *payload=array+0x14+pos;
    if(cmd==90){
        size_t n=count-pos;
        if(n<6||payload[0]!=4)return 0;
        uint32_t len=(uint32_t)payload[2]<<24|(uint32_t)payload[3]<<16|(uint32_t)payload[4]<<8|payload[5];
        if(len!=n-6)return 0;
        NSData *data=[NSData dataWithBytes:payload+6 length:len];
        @synchronized(AGLobby.class){
            if(atlasRequest[v]!=connection)return 0;
            atlasRequest[v]=0;
            atlasConnection[v]=connection;gearAtlas[v]=data;
        }
        NSString *encoded=[data base64EncodedStringWithOptions:0];
        dispatch_async(dispatch_get_main_queue(),^{
            AGLobby *panel;
            @synchronized(AGLobby.class){panel=activePanel;}
            if(panel.variant==v&&panel.tab==AGLobbyField&&panel.connection==connection)
                [panel.web evaluateJavaScript:[NSString stringWithFormat:@"lobbyGearAtlas('%@')",encoded] completionHandler:nil];
        });
        return 1;
    }
    NSData *body=[NSData dataWithBytes:array+0x14+pos length:count-pos];
    const uint8_t *p=body.bytes;
    if(cmd==105){
        if(body.length!=16)return 0;
        uint64_t xu=0,luong=0;
        for(int i=0;i<8;i++){xu=xu<<8|p[i];luong=luong<<8|p[8+i];}
        if(xu>INT64_MAX||luong>INT64_MAX)return 0;
        dispatch_async(dispatch_get_main_queue(),^{
            AGLobbyAccount next=active.account;
            next.xu=(int64_t)xu;next.luong=(int64_t)luong;
            active.account=next;
            if(active.loaded){
                NSString *js=[NSString stringWithFormat:@"lobbyBalance('%llu','%llu')",(unsigned long long)xu,(unsigned long long)luong];
                [active.web evaluateJavaScript:js completionHandler:nil];
            }
        });
        return 0;
    }
    if(cmd==-14&&p[0]!=3)return 0;
    if(fight==connection && cmd==-120 && (body.length==9||body.length==10) && !memcmp(p,"CT46\x08\0\0\0\0",9)){
        @synchronized(AGLobby.class){
            battlefield[v]=0;
            returnToBoard[v]=connection;
            fieldResult[v]=body.length==10?(int8_t)p[9]:NoFieldResult;
        }
        return 1;
    }
    if(!active||active.variant!=v||active.connection!=connection)return 0;
    if(cmd==-120 && body.length==9 && !memcmp(p,"CT46",4) && p[4]==6){
        uint32_t serial;memcpy(&serial,p+5,4);
        BOOL watching=NO;
        @synchronized(AGLobby.class){
            if(activePanel!=active||active.closing||!serial)return 1;
            if(active.watchSerial==serial){
                active.watching=watching=YES;
                active.watchDeadline=NSProcessInfo.processInfo.systemUptime+20;
                atomic_store(&opened[v],0);
            }
            else if(active.challengeSerial==serial)battlefield[v]=connection;
            else return 1;
            active.closing=!watching;
            active.watchSerial=active.challengeSerial=0;
        }
        if(watching){
            dispatch_async(dispatch_get_main_queue(),^{
                if(!active.watching)return;
                active.overlay.hidden=YES;
                if(!active.host.hidden)[active.host makeKeyWindow];
            });
            AGViewerExpectBattlefield(v,connection);
            return 1;
        }
        dispatch_async(dispatch_get_main_queue(),^{[active close];});return 1;
    }
    NSString *blob=[body base64EncodedStringWithOptions:0];
    NSString *auras=cmd==-14?eventAuras(body,v,connection):@"[]";
    dispatch_async(dispatch_get_main_queue(),^{
        if(!active.web||active.watching)return;
        NSString *js=[NSString stringWithFormat:@"receiveFrame(%d,'%@',%@)",cmd,blob,auras];
        [active.web evaluateJavaScript:js completionHandler:^(id val,NSError *err){if(err)[active close];}];
    });
    return 1;
}

@implementation AGLobby
- (void)open{
    @synchronized(AGLobby.class){
        opening=NO;
        if(connections[self.variant]!=self.connection){atomic_store(&opened[self.variant],0);return;}
        activePanel=self;
    }
    self.host=UIApplication.sharedApplication.keyWindow;
    if(!self.host){[self close];return;}
    NSURL *url=[[NSBundle bundleForClass:self.class] URLForResource:@"lobby" withExtension:@"html" subdirectory:@"viewer"];
    if(!url){[self close];return;}
    WKWebViewConfiguration *config=[WKWebViewConfiguration new];config.websiteDataStore=[WKWebsiteDataStore nonPersistentDataStore];
    [config.userContentController addScriptMessageHandler:self name:@"lobby"];
    self.web=[[WKWebView alloc] initWithFrame:CGRectZero configuration:config];self.web.navigationDelegate=self;
    self.view.backgroundColor=UIColor.clearColor;
    self.web.opaque=NO;self.web.backgroundColor=UIColor.clearColor;
    self.web.scrollView.scrollEnabled=NO;self.web.scrollView.bounces=NO;
    self.web.scrollView.contentInsetAdjustmentBehavior=UIScrollViewContentInsetAdjustmentNever;
    [self.view addSubview:self.web];
    if(@available(iOS 13.0,*)){if(self.host.windowScene)self.overlay=[[AGGameWindow alloc] initWithWindowScene:self.host.windowScene];}
    if(!self.overlay)self.overlay=[[AGGameWindow alloc] initWithFrame:self.host.bounds];
    ((AGGameWindow *)self.overlay).passesGameKeys=YES;
    AGViewportWheelVisible(1);
    self.overlay.rootViewController=self;self.overlay.windowLevel=UIWindowLevelAlert;
    [self.overlay makeKeyAndVisible];[self.web loadFileURL:url allowingReadAccessToURL:url.URLByDeletingLastPathComponent];
}
- (void)viewDidLayoutSubviews{
    [super viewDidLayoutSubviews];
    CGRect game=AGGameRect(self.view);self.web.frame=game;
    ((AGGameWindow *)self.overlay).gameBottom=CGRectGetMaxY(game);
}
- (void)close{
    @synchronized(AGLobby.class){
        if(activePanel!=self)return;
        self.closing=YES;
        self.outgoing=nil;
        self.watchSerial=self.challengeSerial=0;
    }
    if(self.overlay)AGViewportWheelVisible(0);
    BOOL restore=self.overlay.isKeyWindow;
    [self.web.configuration.userContentController removeScriptMessageHandlerForName:@"lobby"];
    [self.web stopLoading];self.web.navigationDelegate=nil;[self.web removeFromSuperview];self.web=nil;
    self.overlay.hidden=YES;self.overlay.rootViewController=nil;self.overlay=nil;
    if(self.isViewLoaded)self.view=nil;
    if(restore && !self.host.hidden)[self.host makeKeyWindow];
    @synchronized(AGLobby.class){
        activePanel=nil;
        atomic_store(&opened[self.variant],0);
    }
}
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView{[self close];}
- (void)webView:(WKWebView *)web didFailNavigation:(WKNavigation *)navigation withError:(NSError *)error{[self close];}
- (void)webView:(WKWebView *)web didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error{[self close];}
- (void)webView:(WKWebView *)web didFinishNavigation:(WKNavigation *)navigation{
    if(web!=self.web||self.loaded)return;
    NSString *tab=self.tab==AGLobbyField?@"field":self.tab==AGLobbyMarket?@"market":@"event";
    AGLobbyAccount account=self.account;
    NSString *outcome=self.fieldResult==NoFieldResult?@"null":[NSString stringWithFormat:@"%d",self.fieldResult];
    NSString *start=[NSString stringWithFormat:@"lobbyViewport(%d,[%d,%d,%d,%d,%d,%d,%d],%d);openTab('%@',%d,%u,%@);lobbyBalance('%lld','%lld')",
                     account.canvasWidth,account.inventoryGeometry[0],account.inventoryGeometry[1],account.inventoryGeometry[2],account.inventoryGeometry[3],account.inventoryGeometry[4],account.inventoryGeometry[5],account.inventoryGeometry[6],account.canvasHeight,tab,account.character,self.firstSerial,outcome,(long long)account.xu,(long long)account.luong];
    self.loaded=YES;
    [web evaluateJavaScript:start completionHandler:^(id value,NSError *error){if(error)[self close];}];
    if(self.tab==AGLobbyField){
        NSString *atlas;
        @synchronized(AGLobby.class){
            if(atlasConnection[self.variant]==self.connection)atlas=[gearAtlas[self.variant] base64EncodedStringWithOptions:0];
        }
        if(atlas)[web evaluateJavaScript:[NSString stringWithFormat:@"lobbyGearAtlas('%@')",atlas] completionHandler:nil];
    }
}
- (void)webView:(WKWebView *)web decidePolicyForNavigationAction:(WKNavigationAction *)action decisionHandler:(void (^)(WKNavigationActionPolicy))decision{
    NSURL *allowed=[[NSBundle bundleForClass:self.class] URLForResource:@"lobby" withExtension:@"html" subdirectory:@"viewer"];
    decision([action.request.URL isEqual:allowed]?WKNavigationActionPolicyAllow:WKNavigationActionPolicyCancel);
}
- (void)userContentController:(WKUserContentController *)ctrl didReceiveScriptMessage:(WKScriptMessage *)message{
    if(message.webView!=self.web||!message.frameInfo.isMainFrame||![message.body isKindOfClass:NSArray.class])return;
    NSArray *args=message.body;
    if(args.count==2&&[args[0] isEqual:@"profileDiagnostic"]&&[args[1] isKindOfClass:NSDictionary.class]){
        if(activePanel==self&&!self.watching)AGSaveProfileDiagnostic(self,args[1]);return;
    }
    if(args.count==2&&[args[0] isEqual:@"profileIcons"]&&[args[1] isKindOfClass:NSDictionary.class]){
        if(activePanel!=self||self.watching||self.closing||self.tab!=AGLobbyField)return;
        NSDictionary *input=args[1];id hero=AGProfileNumber(input[@"hero"],0),account=AGProfileNumber(input[@"requested_id"],0),serial=AGProfileNumber(input[@"serial"],0),ids=AGProfileNumber(input[@"ids"],0);
        if(!hero||[hero intValue]<0||[hero intValue]>9||!account||[account intValue]<1||!serial||[serial intValue]<1||![ids isKindOfClass:NSArray.class]||[ids count]!=6)return;
        for(id item in ids)if(![item isKindOfClass:NSNumber.class]||[item intValue]<-1||[item intValue]>32767)return;
        @synchronized(AGLobby.class){self.profileIconRequest=@{@"hero":hero,@"requested_id":account,@"serial":serial,@"ids":ids};}return;
    }
    if(args.count==2&&[args[0] isKindOfClass:NSString.class]&&[args[0] isEqual:@"close"]){[self close];return;}
    if(args.count==2&&[args[0] isEqual:@"edit"]&&[args[1] isKindOfClass:NSDictionary.class]){
        NSDictionary *input=args[1];
        NSNumber *serial=input[@"serial"],*limit=input[@"maxLength"];
        NSString *value=input[@"value"],*type=input[@"type"];
        if(![serial isKindOfClass:NSNumber.class]||serial.longLongValue<1||serial.longLongValue>INT32_MAX||
           ![limit isKindOfClass:NSNumber.class]||limit.intValue<1||limit.intValue>100||
           ![value isKindOfClass:NSString.class]||value.length>100||![type isKindOfClass:NSString.class]||self.presentedViewController)return;
        __weak AGLobby *weakSelf=self;
        void (^result)(id)=^(id text){
            AGLobby *panel=weakSelf;if(!panel||panel.closing||!panel.web)return;
            NSData *data=[NSJSONSerialization dataWithJSONObject:@[serial,text?:NSNull.null] options:0 error:nil];
            NSString *json=[[NSString alloc]initWithData:data encoding:NSUTF8StringEncoding];
            [panel.web evaluateJavaScript:[NSString stringWithFormat:@"lobbyInputResult(...%@)",json] completionHandler:nil];
        };
        UIAlertController *alert=[UIAlertController alertControllerWithTitle:@"Nhập" message:nil preferredStyle:UIAlertControllerStyleAlert];
        [alert addTextFieldWithConfigurationHandler:^(UITextField *field){
            field.text=value;field.secureTextEntry=[type isEqual:@"password"];
            field.autocorrectionType=UITextAutocorrectionTypeNo;field.autocapitalizationType=UITextAutocapitalizationTypeNone;
            field.keyboardType=[input[@"numeric"] isEqual:@YES]?UIKeyboardTypeNumberPad:UIKeyboardTypeDefault;
            field.returnKeyType=UIReturnKeyDone;
        }];
        __weak UIAlertController *weakAlert=alert;
        [alert addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:^(UIAlertAction *action){
            NSString *text=weakAlert.textFields.firstObject.text?:@"";
            if(text.length>limit.unsignedIntegerValue)text=[text substringToIndex:limit.unsignedIntegerValue];
            weakAlert.textFields.firstObject.text=@"";result(text);
        }]];
        [alert addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:^(UIAlertAction *action){weakAlert.textFields.firstObject.text=@"";result(nil);}]];
        [self presentViewController:alert animated:YES completion:nil];return;
    }
    if(args.count!=2||![args[0] isKindOfClass:NSNumber.class]||![args[1] isKindOfClass:NSString.class]||[args[1] length]>1400)return;
    int cmd=[args[0] intValue];NSData *data=[[NSData alloc]initWithBase64EncodedString:args[1] options:0];
    if(!data.length||(cmd!=-120&&cmd!=-121&&cmd!=-14&&cmd!=5))return;
    @synchronized(AGLobby.class){
        if(activePanel!=self||self.closing||self.watching||self.outgoing)return;
        self.watchSerial=0;self.challengeSerial=0;
        if(cmd==-120 && (data.length==17||data.length==18)){
            const uint8_t *p=data.bytes;
            uint32_t serial;memcpy(&serial,p+5,4);
            if(p[4]==6)self.watchSerial=serial;
            if(p[4]==3)self.challengeSerial=serial;
        }
        self.command=cmd;self.outgoing=data;
    }
}
@end



