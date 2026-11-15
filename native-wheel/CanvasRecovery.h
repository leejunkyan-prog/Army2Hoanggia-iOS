#pragma once
#include <stdint.h>
typedef struct {
    uint64_t attempts,recovered,failures;
    int armed,pending,status,registered;
} AGCanvasRecovery;
#ifdef AG_CANVAS_RECOVERY
void AGCanvasRecoveryTrack(void *env,int variant);
void AGCanvasRecoveryFrame(void *env,int variant,int watching);
int AGCanvasRecoveryCopy(int variant,AGCanvasRecovery *out);
#else
static inline void AGCanvasRecoveryTrack(void *e,int v){}
static inline void AGCanvasRecoveryFrame(void *e,int v,int w){}
#endif
