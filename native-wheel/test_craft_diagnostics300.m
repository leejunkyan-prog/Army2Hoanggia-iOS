#import <UIKit/UIKit.h>
#include <string.h>
#include <stdlib.h>
#include "CraftDiagnostics.h"
#include "ReturnDiagnostics.h"
static uint8_t original[0xd0],resolved[0xd0],message[0x40],stream[0x30],array[0x80];
static int64_t native[CF_COUNT];
int AGInventoryCraftInspect(int v,void *item,int64_t fields[CF_COUNT]){
    memset(fields,0,sizeof native);if(v!=0)return 0;memcpy(fields,native,sizeof native);
    fields[CF_OPAQUE_IS_SLOT]=item==resolved;fields[CF_OPAQUE_IN_SOURCE]=item==resolved;return 1;
}
int AGWheelGuard(void *e,int (*fn)(void *,void *),void *job,void *unused){return fn(e,job);}
static NSString *docs(void){return NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;}
static void putPointer(void *p,void *v){memcpy(p,&v,sizeof v);}
@interface Craft300App : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@end
@implementation Craft300App
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options{
    self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];self.window.rootViewController=[UIViewController new];[self.window makeKeyAndVisible];
    original[0xbd]=resolved[0xbd]=1;*(int64_t *)(original+0x80)=*(int64_t *)(resolved+0x80)=238;
    *(int64_t *)(original+0x90)=6;*(int64_t *)(resolved+0x90)=5;
    native[CF_OK]=native[CF_SCREEN]=native[CF_SOURCE_FOUND]=native[CF_SNAPSHOT_STABLE]=1;
    native[CF_SLOT_ID]=238;native[CF_SLOT_QUANTITY]=5;native[CF_SELECTED]=31;native[CF_MENU_VISIBLE]=1;
    AGReturnPulse(0,0);AGReturnPulse(0,1);AGReturnInput(0,0,'A',0);
    AGCraftSample((void *)1,0);AGCraftDetail((void *)1,original,resolved,1,CR_KNOWN_RECIPE);
    putPointer(message+0x20,stream);putPointer(stream+0x10,array);message[0x30]=(uint8_t)-73;
    *(int *)(array+0x10)=64;*(int *)(stream+0x18)=32;*(int *)(stream+0x20)=3;
    memcpy(array+0x14,"PRIVATE_PAYLOAD_DO_NOT_EXPORT",28);
    for(int i=0;i<150;i++)AGCraftReceive(message,0);
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,2200*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
        BOOL passed=YES;NSString *reason=@"";
        @try{
            NSString *path=[docs() stringByAppendingPathComponent:@"Craft300-diagnostic.json"];
            NSData *data=[NSData dataWithContentsOfFile:path];
            NSDictionary *report=data?[NSJSONSerialization JSONObjectWithData:data options:0 error:nil]:nil;
            NSCAssert([report[@"build"] intValue]==300&&[report[@"history"] count]>=2,@"Independent craft logger did not keep writing");
            NSDictionary *pb=report[@"latest"][0],*craft=pb[@"craft"];
            NSCAssert([craft[@"slot_id"] intValue]==238&&[craft[@"slot_quantity"] intValue]==5,@"Missing native selected recipe metadata");
            NSCAssert([craft[@"detail_calls"] intValue]==1&&[craft[@"classifier_accepted"] intValue]==1,@"Classifier result was lost");
            NSCAssert([report[@"craft_events"] count]==128,@"Event ring is not bounded");
            NSDictionary *event=[report[@"craft_events"] lastObject];
            NSCAssert([event[@"command"] intValue]==-73&&[event[@"remaining_bytes"] intValue]==29,@"Wrong observed command metadata");
            NSString *text=[[NSString alloc]initWithData:data encoding:NSUTF8StringEncoding];
            NSCAssert(![text containsString:@"PRIVATE_PAYLOAD_DO_NOT_EXPORT"]&&[pb[@"soft_key"] intValue]==0,@"Packet body or typed characters leaked into export");
            NSCAssert([pb[@"game_ticks"] intValue]==1&&[pb[@"game_age_ms"] intValue]>=700,@"Logger fabricated game progress");
            NSCAssert(*(int *)(stream+0x20)==3&&self.window.isKeyWindow&&app.keyWindow==self.window,@"Logger mutated stream or game window ownership");
            AGReturnDiagnosticSave();
            reason=@"Automatic Craft300 JSON/history while callbacks idle, native item and classifier metadata, bounded128 receive events, stream cursor/window retained, no packet body or typed-character export";
        }@catch(NSException *e){passed=NO;reason=e.reason?:e.name;}
        NSDictionary *result=@{@"passed":@(passed),@"reason":reason};
        [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil] writeToFile:[docs() stringByAppendingPathComponent:@"craft300-result.json"] atomically:YES];exit(passed?0:1);
    });
    return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(Craft300App.class));}}
