#import <UIKit/UIKit.h>
#include <stdlib.h>
#include "ReturnDiagnostics.h"
@interface Diagnostic297App : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@end
@implementation Diagnostic297App
- (BOOL)application:(UIApplication *)app didFinishLaunchingWithOptions:(NSDictionary *)options {
    self.window=[[UIWindow alloc]initWithFrame:UIScreen.mainScreen.bounds];
    self.window.rootViewController=[UIViewController new];[self.window makeKeyAndVisible];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC/5),dispatch_get_main_queue(),^{
        __block BOOL passed=YES;__block NSString *reason=@"";
        @try{
            int fields[RD_COUNT]={0};fields[RD_OK]=1;fields[RD_SCREEN]=1;fields[RD_ROWS]=130;fields[RD_VISIBLE]=1;
            AGReturnPulse(0,0);AGReturnPulse(0,1);AGReturnInput(0,0,-7,1);AGReturnPublish(0,fields);
            AGReturnDiagnosticSave();
            NSString *docs=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
            NSString *path=[docs stringByAppendingPathComponent:@"Watch297-diagnostic.json"];
            NSDictionary *report=[NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:path] options:0 error:nil];
            NSDictionary *pb=[report[@"latest"] firstObject];
            NSCAssert([report[@"build"] intValue]==297&&[pb[@"area_rows"] intValue]==130,@"Diagnostic file failed to capture installed areas");
            NSCAssert([pb[@"soft_key"] intValue]==-7&&[pb[@"input_blocker"] intValue]==1,@"Input blocker was not written");
            NSCAssert(self.window.isKeyWindow&&app.keyWindow==self.window,@"Logger changed game window ownership");
            AGReturnInput(0,0,'A',0);AGReturnDiagnosticSave();
            report=[NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:path] options:0 error:nil];
            pb=[report[@"latest"] firstObject];
            NSCAssert([pb[@"soft_key"] intValue]==0&&[report[@"history"] count]>=2,@"Unsafe typed-input logging or missing history");
            reason=@"Local timestamped JSON/history, native130-area state, input-blocker metadata, no typed characters and original key window retained";
        }@catch(NSException *e){passed=NO;reason=e.reason?:e.name;}
        NSString *docs=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW,2100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
            @try{
                if(passed){
                    NSData *data=[NSData dataWithContentsOfFile:[docs stringByAppendingPathComponent:@"Watch297-diagnostic.json"]];
                    NSDictionary *report=[NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
                    NSDictionary *pb=[report[@"latest"] firstObject];
                    NSCAssert([report[@"history"] count]>=3,@"Independent UIKit timer did not continue writing");
                    NSCAssert([pb[@"game_ticks"] intValue]==1&&[pb[@"render_ticks"] intValue]==1,@"Logger fabricated native callback progress");
                    NSCAssert([pb[@"game_age_ms"] intValue]>=700&&[pb[@"render_age_ms"] intValue]>=700,@"Stalled native callback ages were not retained");
                    NSCAssert(self.window.isKeyWindow&&app.keyWindow==self.window,@"Timer changed original key window");
                    reason=[reason stringByAppendingString:@"; independent timer continues while game/render callbacks remain stopped"];
                }
            }@catch(NSException *e){passed=NO;reason=e.reason?:e.name;}
            NSDictionary *result=@{@"passed":@(passed),@"reason":reason};
            [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil] writeToFile:[docs stringByAppendingPathComponent:@"diagnostics297-result.json"] atomically:YES];
            exit(passed?0:1);
        });
    });
    return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(Diagnostic297App.class));}}
