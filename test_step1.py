from deepseeker import DeepSeekerConfig, DeepSeekerStep1


def main() -> None:
    cfg = DeepSeekerConfig(    
        openai_api_key="sk-ebba1b518e7b49198a60767dd5f9c35b",
        openai_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    engine = DeepSeekerStep1(cfg)

    question = input("请输入你的问题: ")
    result = engine.run(question)

    print("\n=== LLM0 原始输出 ===")
    print(result.raw_response)
    print("\n=== 决策结果 ===")
    print(f"decision: {result.decision}")
    if result.tool_call:
        print("tool_call:", result.tool_call)


if __name__ == "__main__":
    main()
