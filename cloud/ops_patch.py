# 给旧版 comfy/ops.py 的 disable_weight_init 与 manual_cast 两个类
# 各加一个 RMSNorm 嵌套类（适配旧版，不依赖 run_every_op / uncast_bias_weight / comfy_aimdo）。
# 旧版里 manual_cast / fp8_ops 是模块级类(0缩进)，RMSNorm 作为它们的嵌套类(4缩进)。
p = "/root/ComfyUI/comfy/ops.py"
s = open(p, encoding="utf-8").read()

# disable_weight_init 内的 RMSNorm（4空格缩进），插在模块级 class manual_cast 之前
rmsnorm_disable = (
    '    class RMSNorm(torch.nn.RMSNorm, CastWeightBiasOp):\n'
    '        def reset_parameters(self):\n'
    '            self.bias = None\n'
    '            return None\n'
    '\n'
    '        def forward_comfy_cast_weights(self, input):\n'
    '            if self.weight is not None:\n'
    '                weight, bias = cast_bias_weight(self, input)\n'
    '            else:\n'
    '                weight = None\n'
    '                bias = None\n'
    '            return torch.nn.functional.rms_norm(input, self.normalized_shape, weight, self.eps)\n'
    '\n'
    '        def forward(self, *args, **kwargs):\n'
    '            if self.comfy_cast_weights:\n'
    '                return self.forward_comfy_cast_weights(*args, **kwargs)\n'
    '            else:\n'
    '                return super().forward(*args, **kwargs)\n'
    '\n'
)

anchor1 = "class manual_cast(disable_weight_init):"
assert anchor1 in s, "anchor1 missing"
s = s.replace(anchor1, rmsnorm_disable + anchor1, 1)

# manual_cast 内的 RMSNorm（4空格缩进），插在模块级 class fp8_ops 之前
rmsnorm_manual = (
    '    class RMSNorm(disable_weight_init.RMSNorm):\n'
    '        comfy_cast_weights = True\n'
    '\n'
)

anchor2 = "class fp8_ops(manual_cast):"
assert anchor2 in s, "anchor2 missing"
s = s.replace(anchor2, rmsnorm_manual + anchor2, 1)

open(p, "w", encoding="utf-8").write(s)
print("OPS_PATCH_OK")
