from app.core.database import Base, SessionLocal, engine
from app.models.question import Question

QUESTIONS = [
    {
        "module": "os",
        "chapter": "进程与线程",
        "type": "choice",
        "stem": "关于进程和线程，下列说法正确的是？",
        "options": {
            "A": "进程是 CPU 调度的基本单位，线程是资源分配的基本单位",
            "B": "线程是 CPU 调度的基本单位，进程是资源分配的基本单位",
        },
        "answer": "B",
        "explanation": "进程是资源分配单位，线程是 CPU 调度单位，同一进程内的线程共享地址空间。",
        "difficulty": 1,
    },
    {
        "module": "network",
        "chapter": "TCP",
        "type": "choice",
        "stem": "TCP 建立连接需要几次握手？",
        "options": {"A": "1 次", "B": "2 次", "C": "3 次", "D": "4 次"},
        "answer": "C",
        "explanation": "三次握手：客户端发 SYN、服务端回 SYN+ACK、客户端再回 ACK。",
        "difficulty": 1,
    },
    {
        "module": "db",
        "chapter": "索引",
        "type": "choice",
        "stem": "MySQL InnoDB 默认用什么数据结构做索引？",
        "options": {"A": "哈希表", "B": "B+ 树", "C": "红黑树", "D": "跳表"},
        "answer": "B",
        "explanation": "B+ 树矮胖减少磁盘 I/O，叶子链表支持范围查询。",
        "difficulty": 2,
    },
    {
        "module": "algorithm",
        "chapter": "排序",
        "type": "choice",
        "stem": "快速排序平均时间复杂度是？",
        "options": {"A": "O(n)", "B": "O(n log n)", "C": "O(n²)", "D": "O(log n)"},
        "answer": "B",
        "explanation": "快排平均 O(n log n)，最坏 O(n²)。",
        "difficulty": 1,
    },
    {
        "module": "pattern",
        "chapter": "创建型",
        "type": "choice",
        "stem": "单例模式属于哪类设计模式？",
        "options": {"A": "创建型", "B": "结构型", "C": "行为型"},
        "answer": "A",
        "explanation": "创建型关注对象创建，包括单例、工厂、建造者等。",
        "difficulty": 1,
    },
    {
        "module": "os",
        "chapter": "死锁",
        "type": "short_answer",
        "stem": "产生死锁的四个必要条件是什么？",
        "options": None,
        "answer": "互斥、持有并等待、不可剥夺、循环等待。破坏任意一个即可预防死锁。",
        "explanation": "面试常考题，四个条件缺一不可。",
        "difficulty": 2,
    },
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Question).count() > 0:
        print("题库已有题目，跳过。")
        return
    db.add_all([Question(**q) for q in QUESTIONS])
    db.commit()
    print(f"成功灌入 {len(QUESTIONS)} 道题。")


if __name__ == "__main__":
    run()
