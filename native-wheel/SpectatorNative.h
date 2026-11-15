#pragma once
#include <stddef.h>
#include <stdint.h>
int AGNativeWatchAvailable(void);
int AGNativeWatchFree(int variant);
int AGNativeWatchRunning(int variant);
int AGNativeWatchAngle(int variant);
int AGNativeWatchPacket(void *env,int variant,const uint8_t *data,size_t length);
int AGNativeWatchReplay(void *env,int variant,int command,const uint8_t *data,size_t length);
int AGNativeWatchFinishSnapshot(void *env,int variant);
int AGNativeWatchTryFinishSnapshot(void *env,int variant);
void AGNativeWatchObserve(int variant,int command,const uint8_t *data,size_t length);
void AGNativeWatchOption(int variant,int option);
int AGNativeWatchAux(int variant);
void AGNativeWatchSwitch(void *env,int variant);
void AGNativeWatchEnd(void *env,int variant);
int AGNativeWatchTryEnd(void *env,int variant);
/* -1: navigated elsewhere; 0: room0 has no rows; positive: installed rows. */
int AGNativeWatchRoomStatus(void *env,int variant);
void AGNativeWatchCamera(int variant,int kind,int code);
int AGNativeWatchToggleCamera(int variant);
void AGNativeWatchClearCameraKeys(int variant);
void AGNativeWatchNudgeCamera(int variant,int code);
void AGNativeWatchTick(void *env,int variant);
/* Spectator simulation follows the visible native render callback. */
__attribute__((visibility("default"))) void AGNativeWatchRenderFrame(void *env,int variant);
__attribute__((visibility("default"))) void AGNativeWatchGameUpdate(void *env,void *arena,int variant);
int AGNativeWatchRendering(int variant);
int AGViewerActive(int variant);

