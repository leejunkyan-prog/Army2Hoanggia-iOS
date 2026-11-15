#pragma once
#include <stdint.h>
/* B281: audited inventory singleton statics and selection refresh. */
static const uintptr_t inventoryMaps[6][3]={
{0x2094ac0,0x592220,0x2091350},
{0x20c34f0,0x67b7dc,0x20c0000},
{0x20f11e0,0x7604a0,0x20edcf0},
{0x211eed0,0x845164,0x211b9e0},
{0x214cbc0,0x929e28,0x21496d0},
{0x217a8b0,0xa0eaec,0x21773c0},
};
/* Recipe screen singleton getters and Z5.i were checked in all six AOT
   variants. The inventory parent is at +0x50, not the callback's +0x10. */
static const uintptr_t recipeClasses[6]={
0x2087cf0,0x20b6f10,0x20e4c00,0x21128f0,0x21405e0,0x216e2d0
};

