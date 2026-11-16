#pragma once
#include <stdint.h>
typedef struct {int status,width,height,iconID;uint8_t *rgba;} AGProfileIcon;
/* Called only with the original Env on its game worker. Caller frees rgba. */
int AGProfileIconRead(void *env,int variant,int hero,int slot,int id,AGProfileIcon *out);
int AGProfileAvatarRead(void *env,int variant,int hero,const int parts[5],AGProfileIcon *out);
int AGProfileAvatarPoseRead(void *env,int variant,int hero,const int parts[5],int pose,int mode,AGProfileIcon *out);
int AGNativeImageRGBA(void *env,void *image,int x,int y,int width,int height,AGProfileIcon *out);
