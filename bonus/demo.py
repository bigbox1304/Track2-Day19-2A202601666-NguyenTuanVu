"""Five-query demonstration for the hybrid memory POC."""
import sys

from agent import HybridMemoryAgent


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    agent = HybridMemoryAgent()
    memories = [
        "Tôi đã đọc về Kubernetes và cách autoscaling hạ tầng cloud theo lưu lượng.",
        "Ghi chú về cloud security: dùng IAM least privilege, network policy và zero trust.",
        "Tài liệu DevOps nói về Docker, CI/CD pipeline và blue-green deployment.",
        "Tôi đang học vector search, embeddings và RRF để xây ứng dụng AI tiếng Việt.",
    ]
    for text in memories:
        agent.remember(text)

    queries = [
        "Tôi đã đọc gì về Kubernetes?",
        "Recommend đọc gì tiếp",
        "Tôi đang quan tâm gì gần đây?",
        "Tài liệu về tự động mở rộng hạ tầng?",
        "Cho tôi summary cloud security",
    ]
    for index, query in enumerate(queries, start=1):
        print(f"\n=== Query {index}: {query}")
        print(agent.recall(query))


if __name__ == "__main__":
    main()
