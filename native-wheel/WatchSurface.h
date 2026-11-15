#pragma once
#import <UIKit/UIKit.h>
@interface AGWatchSurface : UIView
@property(nonatomic) BOOL passesGameTouches;
@property(nonatomic) CGFloat gameBottom;
@end
BOOL AGWatchMount(UIViewController *watch,UIWindow *host);
void AGWatchUnmount(UIViewController *watch);
