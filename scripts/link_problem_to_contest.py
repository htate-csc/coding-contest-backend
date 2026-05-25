import sys
import argparse
from sqlmodel import Session, select
from app.core.db import engine
from app.models import Contest, Problem, ContestProblems

def main():
    parser = argparse.ArgumentParser(description="コンテストに問題を紐付けるスクリプト")
    parser.add_argument("--contest", required=True, help="コンテスト名（タイトル）")
    parser.add_argument("--problem", required=True, help="問題名")
    parser.add_argument("--order", type=int, default=None, help="問題の順序（指定しない場合は現在の問題数+1）")
    
    args = parser.parse_args()
    
    with Session(engine) as session:
        # 1. コンテストの検索
        # 完全一致で検索
        contest = session.exec(
            select(Contest).where(Contest.title == args.contest, Contest.is_deleted == False)
        ).first()
        
        if not contest:
            # 部分一致で検索
            contests = session.exec(
                select(Contest).where(Contest.title.contains(args.contest), Contest.is_deleted == False)
            ).all()
            if not contests:
                print(f"エラー: コンテスト '{args.contest}' が見つかりませんでした。")
                sys.exit(1)
            elif len(contests) > 1:
                print(f"エラー: 複数のコンテストが見つかりました:")
                for c in contests:
                    print(f"  - ID: {c.id}, タイトル: {c.title}")
                print("完全なタイトルを指定して再試行してください。")
                sys.exit(1)
            else:
                contest = contests[0]
                print(f"コンテストが見つかりました: '{contest.title}' (ID: {contest.id})")
        else:
            print(f"コンテスト: '{contest.title}' (ID: {contest.id})")
            
        # 2. 問題の検索
        problem = session.exec(
            select(Problem).where(Problem.name == args.problem)
        ).first()
        
        if not problem:
            # 部分一致で検索
            problems = session.exec(
                select(Problem).where(Problem.name.contains(args.problem))
            ).all()
            if not problems:
                print(f"問題 '{args.problem}' が見つかりませんでした。")
                confirm = input("問題を新規に作成してコンテストに紐付けますか？ (y/N): ")
                if confirm.lower() != 'y':
                    print("キャンセルしました。")
                    sys.exit(1)
                
                # 新規作成用データの入力
                print("\n--- 新規問題の作成 ---")
                name = input(f"問題名 [{args.problem}]: ") or args.problem
                try:
                    time_limit = float(input("実行時間制限 (ms) [2000]: ") or "2000")
                except ValueError:
                    print("無効な数値です。2000を使用します。")
                    time_limit = 2000.0
                
                try:
                    memory_limit = int(input("メモリ制限 (GB) [1]: ") or "1")
                except ValueError:
                    print("無効な数値です。1を使用します。")
                    memory_limit = 1
                
                content = input("問題文 (content): ")
                input_format = input("入力フォーマット (input_format): ")
                output_format = input("出力フォーマット (output_format): ")
                
                print("サンプルテストケース (3件必要です):")
                samples = []
                for i in range(1, 4):
                    print(f"サンプル {i}:")
                    inp = input(f"  入力例 {i}: ")
                    out = input(f"  出力例 {i}: ")
                    samples.append({"input": inp, "output": out})
                
                # DBに問題を作成
                problem = Problem(
                    name=name,
                    time_limit=time_limit,
                    memory_limit=memory_limit,
                    content=content,
                    input_format=input_format,
                    output_format=output_format,
                    samples=samples
                )
                session.add(problem)
                session.commit()
                session.refresh(problem)
                print(f"問題を新規作成しました: '{problem.name}' (ID: {problem.id})")
            elif len(problems) > 1:
                print(f"エラー: 複数の問題が見つかりました:")
                for p in problems:
                    print(f"  - ID: {p.id}, 名前: {p.name}")
                print("完全な名前を指定して再試行してください。")
                sys.exit(1)
            else:
                problem = problems[0]
                print(f"問題が見つかりました: '{problem.name}' (ID: {problem.id})")
        else:
            print(f"問題: '{problem.name}' (ID: {problem.id})")
            
        # 3. 紐付けの登録
        # 既に紐付いているか確認
        existing = session.exec(
            select(ContestProblems).where(
                ContestProblems.contest_id == contest.id,
                ContestProblems.problem_id == problem.id
            )
        ).first()
        
        if existing:
            print(f"警告: 問題 '{problem.name}' はすでにコンテスト '{contest.title}' に紐付けられています。")
            sys.exit(0)
            
        # order_numの決定
        if args.order is None:
            # 現在のコンテスト内の問題数をカウントして、最後尾にする
            current_links = session.exec(
                select(ContestProblems).where(ContestProblems.contest_id == contest.id)
            ).all()
            order_num = len(current_links)
        else:
            order_num = args.order
            
        # 紐付け作成
        link = ContestProblems(
            contest_id=contest.id,
            problem_id=problem.id,
            order_num=order_num
        )
        session.add(link)
        session.commit()
        print(f"成功: 問題 '{problem.name}' をコンテスト '{contest.title}' に紐付けました！ (順序: {order_num})")

if __name__ == "__main__":
    main()
