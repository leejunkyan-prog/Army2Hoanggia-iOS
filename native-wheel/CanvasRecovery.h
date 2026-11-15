#pragma once
#include <stdint.h>
typedef struct {
    uint64_t attempts,recovered,failures;
    int armed,pending,status;
} AGCanvasRecovery;
#ifdef AG_CANVAS_RECOVERY
void AGCanvasRecoveryFrame(void *env,int variant,int watching);
int AGCanvasRecoveryCopy(int variant,AGCanvasRecovery *out);
#else
static inline void AGCanvasRecoveryFrame(void *e,int v,int w){}
#endif
