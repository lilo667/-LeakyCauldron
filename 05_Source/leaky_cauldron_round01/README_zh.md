# 破釜酒吧 · 检查点 1 提案包

《哈利·波特》破釜酒吧（The Leaky Cauldron）主厅的 Blender 场景研究。当前阶段是**灰模 + 灯光 + 机位 + 平面**，用于 2026-11-30 的期末项目检查点；材质、道具与正式渲染在下一阶段完成。

## 打开

用 Blender 5.2 或更新版本打开 `LeakyCauldron_Blockout.blend`。

- 数字小键盘 `0`：进入当前相机（默认 `CAM_01_Hero`）。
- 相机集合 `08_CAMERAS` 里还有壁炉、吧台、反向与平面机位；选中后 `Ctrl + 数字小键盘 0` 设为活动相机。
- `Z` → 材质预览查看材质；编辑时用实体模式更轻。
- `F12` 重新渲染（Cycles / CPU，64 采样，OIDN 降噪）。

## 文件

| 文件 | 说明 |
|---|---|
| `LeakyCauldron_Blockout.blend` | 场景文件，贴图全程序化，无需外部资源 |
| `build_leaky.py` | 生成整个场景的脚本（集合、几何、材质、灯光、机位） |
| `render_views.py` | 从 .blend 渲染主图与平面图 |
| `renders/01_hero_blockout.png` | 主镜头 1440×810 |
| `renders/02_fireplace_blockout.png` | 壁炉与坩埚 1200×675 |
| `renders/03_bar_blockout.png` | 吧台细节 1200×675 |
| `renders/04_plan_blockout.png` | 正交俯视平面 1600×1100 |
| `PROPOSAL_zh.pdf` | 两页检查点简报 |
| `references/` | 参考图、参考板与 `sources.json`（许可信息） |
| `REFERENCES.md` | 参考出处与版权说明 |

## 复现

```bash
# 重建场景（约 2 秒，不含渲染）
blender -b --python build_leaky.py

# 预览三机位（960×540 / 24 采样，约 3 分钟）
blender -b --python build_leaky.py -- --render --preview

# 正式主图 + 平面
blender -b LeakyCauldron_Blockout.blend --python render_views.py
```

## 场景数据

- 727 个对象、706 个网格、28 个材质、5 台相机；基础三角面约 6.9 万（不含修改器细分）。
- 房间 12 × 8 m，净高 3.05 m，梁底 2.55 m。
- 主镜头 1440×810 / 96 采样，M1 CPU 约 5 分钟；960×540 / 64 采样约 50 秒。这些时间只对应本机本次运行。

## 已知限制

- 这是灰模：家具是体块级，缺少雕花、软装与生活痕迹；招牌字体为 Blender 默认字体。
- 壁炉、楼梯与吧台的细节在下一阶段替换为高模；木筋墙将改为 Geometry Nodes 生成。
- 体积雾只做了低密度测试，正式渲染前会重新标定。

## 版权

《哈利·波特》系列、破釜酒吧场景设计及相关标识归 Warner Bros. Entertainment 与 J.K. Rowling 等权利人所有。本项目仅用于计算机图形学课程学习与技法研究，不用于商业用途；参考图仅作比对，未导入场景。
