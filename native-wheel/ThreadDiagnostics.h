#pragma once
#ifdef AG_RETURN_THREAD_DIAGNOSTIC
void AGThreadPulse(int variant,int source);
int AGThreadGameExited(int variant);
int AGThreadRebindGame(int variant);
#ifdef __OBJC__
#import <Foundation/Foundation.h>
/* Called only by the serial diagnostic file worker. */
NSArray *AGThreadDiagnosticsSample(void);
#endif
#else
static inline void AGThreadPulse(int v,int source){}
#endif
