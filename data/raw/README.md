# 官方原始数据

本目录不提交官方压缩包或题面副本。请运行：

```bash
python scripts/download_official_data.py
npm install
python scripts/prepare_official_data.py
```

下载脚本会保存文件并进行 SHA-256 校验；提取脚本只接受校验通过的文件。

| 年份 | 官网页面 | 官方附件直链 | SHA-256 |
|---|---|---|---|
| 2016 | https://www.mcm.edu.cn/html_cn/node/6d026d84bd785435f92e3079b4a87a2b.html | https://www.mcm.edu.cn/upload_cn/node/393/UxYMjfW4fd0a5cd7a21951b49232088d2af3f4e8.rar | `a20eac15b174e79ac5491378dfec5138c1f990d8f55d2ba037cadb69cb685dad` |
| 2023 | https://www.mcm.edu.cn/html_cn/node/c74d72127066f510a5723a94b5323a26.html | https://www.mcm.edu.cn/upload_cn/node/690/Y20WPner9fa62862794e6dc82731a5561ce1132f.rar | `37b1010672adcf35831e798264cc69db616027f2287cfeae3c4ee6daf03ae4e6` |
| 2024 | https://www.mcm.edu.cn/html_cn/node/a0c1fb5c31d43551f08cd8ad16870444.html | https://www.mcm.edu.cn/upload_cn/node/725/pmkWxf8H9cfe9984c1a1a5b1263e5dd3b5596ed5.zip | `38d9effcede947354f9e9a9c2b4fc68947d83a77c2ff75737e9a662888158726` |

## 使用边界

- 数据版权归原发布方所有，本仓库只保存下载地址、校验值、字段字典和可复算派生结果。
- 2016A 的官方题包只有题面，没有独立数据附件；模型参数直接来自题面。
- `data/processed/` 中的文件是代码生成的聚合结果，不替代官方附件。
