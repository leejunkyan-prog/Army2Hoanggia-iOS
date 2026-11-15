#import "WatchSurface.h"
@implementation AGWatchSurface
- (instancetype)initWithFrame:(CGRect)frame {
    if((self=[super initWithFrame:frame])){self.opaque=NO;self.backgroundColor=UIColor.clearColor;self.gameBottom=CGFLOAT_MAX;}
    return self;
}
- (UIView *)hitTest:(CGPoint)point withEvent:(UIEvent *)event {
    if(self.passesGameTouches||point.y>=self.gameBottom)return nil;
    return [super hitTest:point withEvent:event];
}
@end
BOOL AGWatchMount(UIViewController *watch,UIWindow *host){
    UIViewController *parent=host.rootViewController;
    if(!watch||!parent||parent==watch||watch.parentViewController)return NO;
    [parent addChildViewController:watch];
    watch.view.frame=parent.view.bounds;
    watch.view.autoresizingMask=UIViewAutoresizingFlexibleWidth|UIViewAutoresizingFlexibleHeight;
    [parent.view addSubview:watch.view];
    [watch didMoveToParentViewController:parent];
    return YES;
}
void AGWatchUnmount(UIViewController *watch){
    [watch willMoveToParentViewController:nil];
    [watch.view removeFromSuperview];
    [watch removeFromParentViewController];
}
