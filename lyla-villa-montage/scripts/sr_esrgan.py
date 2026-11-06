"""Super-résolution Real-ESRGAN General x4v3 (ONNX, CPU) par tuiles 128x128 avec recouvrement."""
import numpy as np, onnxruntime as ort

class SR:
    def __init__(self, model, threads=4):
        so = ort.SessionOptions(); so.intra_op_num_threads = threads; so.inter_op_num_threads = 1
        self.s = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
        self.name = self.s.get_inputs()[0].name

    def x4(self, img, pad=4):
        """img : uint8 HxWx3 -> uint8 (4H)x(4W)x3. Tuiles 128x128, recouvrement `pad` px de chaque côté."""
        a = np.asarray(img, np.float32) / 255.
        H, W = a.shape[:2]; T = 128; step = T - 2 * pad
        ny, nx = -(-H // step), -(-W // step)
        Hp, Wp = (ny - 1) * step + T, (nx - 1) * step + T
        p = np.pad(a, ((pad, Hp - H - pad), (pad, Wp - W - pad), (0, 0)), mode="reflect")
        core = np.zeros((ny * step * 4, nx * step * 4, 3), np.float32)
        for j in range(ny):
            for i in range(nx):
                tile = p[j * step:j * step + T, i * step:i * step + T]
                r = self.s.run(None, {self.name: tile.transpose(2, 0, 1)[None]})[0][0].transpose(1, 2, 0)
                core[j * step * 4:(j + 1) * step * 4, i * step * 4:(i + 1) * step * 4] = r[pad * 4:(T - pad) * 4, pad * 4:(T - pad) * 4]
        return (np.clip(core[:H * 4, :W * 4], 0, 1) * 255 + .5).astype(np.uint8)
