# 梁致远 · 个人作品集

AI方向学生，专注计算机图形学、Blender 场景建模、材质灯光与实时渲染。

- GitHub：https://github.com/lilo667
- 在线作品集：部署到 GitHub Pages 后可通过仓库地址访问

## 作品：破釜酒吧场景重建

使用 Blender 完成《哈利·波特》破釜酒吧场景重建，并制作离线可运行的浏览器实时演示。

本人独立负责：

- 场景规划与参考板整理
- 场景与吧台几何建模
- 木材、玻璃、金属等材质制作
- Cycles 灯光与最终渲染
- Blender Python 建模与渲染脚本
- WebGL 离线漫游演示
- 渲染成图与作品集页面制作

## 在线演示

- 浏览器漫游：`02_Offline/LeakyCauldron_Bar.html`
- 作品集入口：`index.html`
- 高分辨率 Cycles 成图：`03_Renders/Bar_Cycles.png`
- Blender 可编辑工程：`01_Blender/LeakyCauldron_Bar.blend`
- 课程提案：`04_Proposal/PROPOSAL_zh.pdf`

## 本地运行

浏览器直接打开 `02_Offline/LeakyCauldron_Bar.html` 可离线运行。

或者在项目根目录启动本地服务器：

```powershell
python -m http.server 4173
```

然后访问：

- http://127.0.0.1:4173/
- http://127.0.0.1:4173/02_Offline/LeakyCauldron_Bar.html

## 演示操作

- 点击“进入酒吧”进入漫游
- WASD：移动
- 鼠标：转头
- R：回到吧台
- Esc：暂停

## 演示视频

演示视频已保存为 `06_Media/demo.mp4`，并嵌入作品集首页。

## 部署到 GitHub Pages

1. 在 GitHub 创建公开仓库并上传本项目。
2. 打开仓库的 Settings → Pages。
3. Build and deployment 中选择 GitHub Actions。
4. 推送到默认分支后等待部署完成。

仓库已包含 `.github/workflows/pages.yml`，可自动发布项目根目录。

## 使用说明与版权

本项目用于计算机图形学课程学习与技术展示，不用于商业用途。
《哈利·波特》及破釜酒吧相关设定归其权利人所有；参考来源和版权说明见
`04_Proposal/REFERENCES.md`。
