/* Run on an iOS Simulator against the production mount/hit-test component. */
#import <UIKit/UIKit.h>
#include <math.h>
#include <stdlib.h>
#import "WatchSurface.h"
@interface GameHost293 : UIViewController
@property(nonatomic) NSUInteger disappearances;
@end
@implementation GameHost293
- (void)viewWillDisappear:(BOOL)animated {[super viewWillDisappear:animated];self.disappearances++;}
@end
@interface OverlayTest293 : UIResponder <UIApplicationDelegate>
@property(nonatomic,strong) UIWindow *window;
@property(nonatomic,strong) CADisplayLink *link;
@property(nonatomic) NSUInteger frames;
@end
@implementation OverlayTest293
- (void)frame:(CADisplayLink *)link {self.frames++;}
- (void)finish:(BOOL)passed reason:(NSString *)reason {
    [self.link invalidate];
    NSDictionary *report=@{@"passed":@(passed),@"reason":reason,@"display_frames":@(self.frames)};
    NSData *data=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil];
    NSString *dir=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
    [data writeToFile:[dir stringByAppendingPathComponent:@"overlay293-result.json"] atomically:YES];
    exit(passed?0:1);
}
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
    self.window=[[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    GameHost293 *game=[GameHost293 new];game.view.backgroundColor=UIColor.blueColor;
    self.window.rootViewController=game;[self.window makeKeyAndVisible];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC),dispatch_get_main_queue(),^{
        @try {
            NSCAssert(self.window.isKeyWindow,@"Game window must start key");
            NSUInteger windows=UIApplication.sharedApplication.windows.count;
            UIViewController *watch=[UIViewController new];
            AGWatchSurface *surface=[[AGWatchSurface alloc] initWithFrame:CGRectZero];watch.view=surface;
            NSCAssert(AGWatchMount(watch,self.window),@"Mount failed");
            NSCAssert(watch.parentViewController==game&&surface.superview==game.view,@"Overlay is not a child of the game");
            NSCAssert(self.window.isKeyWindow&&self.window.rootViewController==game,@"Overlay changed game focus/root");
            NSCAssert(UIApplication.sharedApplication.windows.count==windows,@"Overlay created another window");
            NSCAssert(!surface.opaque&&game.disappearances==0,@"Overlay obscured/disappeared the game");
            surface.gameBottom=300;
            UIView *menu=[[UIView alloc] initWithFrame:CGRectMake(0,0,100,100)];[surface addSubview:menu];
            NSCAssert([surface hitTest:CGPointMake(10,10) withEvent:nil]==menu,@"Menu does not receive touches");
            NSCAssert([surface hitTest:CGPointMake(10,400) withEvent:nil]==nil,@"Native keypad is covered");
            surface.passesGameTouches=YES;
            NSCAssert([surface hitTest:CGPointMake(10,10) withEvent:nil]==nil,@"Auxiliary native dialog is covered");
            surface.passesGameTouches=NO;
            self.link=[CADisplayLink displayLinkWithTarget:self selector:@selector(frame:)];
            [self.link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
            dispatch_after(dispatch_time(DISPATCH_TIME_NOW,NSEC_PER_SEC/2),dispatch_get_main_queue(),^{
                @try {
                    NSCAssert(self.frames>0&&game.disappearances==0,@"Game display loop did not continue");
                    CGRect bounds=game.view.bounds;bounds.size.width-=30;game.view.bounds=bounds;
                    [game.view layoutIfNeeded];
                    NSCAssert(fabs(surface.frame.size.width-game.view.bounds.size.width)<1,@"Overlay did not follow game size");
                    AGWatchUnmount(watch);
                    NSCAssert(watch.parentViewController==nil&&surface.superview==nil,@"Overlay did not detach");
                    NSCAssert(self.window.isKeyWindow&&self.window.rootViewController==game,@"Unmount changed game focus/root");
                    [self finish:YES reason:@"Game window/root retained; display link continues; native keypad/auxiliary touches pass; overlay resizes and detaches"];
                }@catch(NSException *error){[self finish:NO reason:error.reason?:error.name];}
            });
        }@catch(NSException *error){[self finish:NO reason:error.reason?:error.name];}
    });
    return YES;
}
@end
int main(int argc,char **argv){@autoreleasepool{return UIApplicationMain(argc,argv,nil,NSStringFromClass(OverlayTest293.class));}}
