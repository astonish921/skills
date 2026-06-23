# detail-flow-use-image-api

`detail-flow-use-image-api` 是 `detail-flow` 的独立分支，保留了以蓝图为核心、强审计的电商详情页工作流，但改用显式的本地图像 API 来执行主图和切片批次生成。

## 核心行为

- 保留 `detail-flow` 中的两道用户审批关卡
- 沿用 `1:3` 主图加 `9:21` 切片的工作流程
- 使用 `IMAGE_BACKEND` 及各服务商对应的凭证
- 单图生成通过 `detail_flow_use_image_api.py` 执行
- 批量切片通过 `detail_flow_use_image_api.py --manifest` 执行

## 配置

在当前环境或 `.env` 文件中设置 `IMAGE_BACKEND` 及各服务商对应的凭证。完整后端列表参见 `.env.example`。

## 示例

```bash
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py "一张精致的 1:3 产品连续主图" --aspect-ratio "1:3" --filename "product_master_1x3.png" --topic-hint "智能风扇"
python skills/detail-flow-use-image-api/detail_flow_use_image_api.py --manifest "project/smart-fan/images/image_prompts.json"
```

## 来源工作流

本技能基于 `detail-flow`，但可独立运行，运行时不依赖 `image-gen-use-api`。


## 使用提示词
读取产品图并理解：D:\04git\test_gemini_image\source1\耳机.png;读取参考效果图并理解：D:\04git\test_gemini_image\source1\狮子带耳机.png,请为这个产品生成一套8屏电商详情页。我想的是用参考图的狮子作为主角，拟人化的手法进行表现，但是不出现人的特征，用动物的动静结合来体验出耳机优秀的音质和降噪能力。详情页整体是比较有趣诙谐好玩的。故事性更像狩猎前夜。