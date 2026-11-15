#pragma once
#include <stdint.h>
typedef struct {
    uint64_t frames,packets,exceptions,waits,expirations;
    int command,operation,waitKind,waitActor,waitStage;
    char exception[512];
} AGWatchTrace;
void AGNativeWatchTraceReset(int variant);
void AGNativeWatchTraceFrame(int variant);
void AGNativeWatchTracePacket(int variant,int command,int operation);
void AGNativeWatchTraceWait(int variant,int kind,int actor,int stage);
int AGNativeWatchTraceCopy(int variant,AGWatchTrace *out);
__attribute__((visibility("default"))) void AGNativeWatchTraceException(void *env,void *exception,int variant);
