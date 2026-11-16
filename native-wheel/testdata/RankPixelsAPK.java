// Extracted color/pixel methods from the user-supplied gs5kl1.apk.
import java.io.*;
public class RankPixelsAPK {
    private static int color(int i) {
        if (i == 1) {
            return 2476799;
        }
        return i == 2 ? 12875519 : 5369233;
    }
    private static int pixel(int i, int i2, boolean z) {
        int i3 = (-16777216) & i;
        if (i3 == 0) {
            return i;
        }
        int i4 = (i >> 16) & 255;
        int i5 = (i >> 8) & 255;
        int i6 = i & 255;
        int i7 = (((i4 * 3) + (i5 * 6)) + i6) / 10;
        if (!z && Math.min(i4, Math.min(i5, i6)) > 235) {
            return i;
        }
        int iMin = Math.min(255, z ? i7 + 20 : ((i7 * 190) / 255) + 65);
        int iColor = color(i2);
        int iMin2 = (((iColor >> 16) & 255) * iMin) / 255;
        int iMin3 = (((iColor >> 8) & 255) * iMin) / 255;
        int iMin4 = ((iColor & 255) * iMin) / 255;
        if (z && i7 > 185) {
            int i8 = (i7 - 185) * 3;
            iMin2 = Math.min(255, iMin2 + i8);
            iMin3 = Math.min(255, iMin3 + i8);
            iMin4 = Math.min(255, iMin4 + i8);
        }
        return (iMin2 << 16) | i3 | (iMin3 << 8) | iMin4;
    }
 public static void main(String[] args) throws Exception {
  DataInputStream in=new DataInputStream(System.in);DataOutputStream out=new DataOutputStream(System.out);
  try { while(true) { int argb=in.readInt();int rank=in.readUnsignedByte();boolean fire=in.readBoolean();out.writeInt(pixel(argb,rank,fire)); } } catch(EOFException done) {}out.flush();
 }
}
