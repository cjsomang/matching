#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse

def collect_source_files(root_dir, extensions, exclude_dirs, exclude_files):
    """
    root_dir 내를 재귀 탐색하여 extensions 목록에 포함된
    파일 경로들을 반환합니다.
    exclude_dirs는 디렉터리 이름 기준,
    exclude_files는 파일 이름 또는 전체 경로 기준으로 제외합니다.
    """
    collected = []
    script_path = os.path.abspath(__file__)
    exclude_files_abs = set(os.path.abspath(f) for f in exclude_files)
    exclude_files_abs.add(script_path)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for fname in filenames:
            full_path = os.path.abspath(os.path.join(dirpath, fname))

            if (any(fname.endswith(ext) for ext in extensions)
                    and full_path not in exclude_files_abs
                    and fname not in exclude_files):  # 이름만 매칭도 고려
                collected.append(full_path)
    return collected

def write_to_txt(file_list, output_path):
    with open(output_path, 'w', encoding='utf-8') as out:
        for file_path in file_list:
            out.write('=' * 80 + '\n')
            out.write(f'FILE: {file_path}\n')
            out.write('-' * 80 + '\n')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    out.write(f.read())
            except Exception as e:
                out.write(f'!! ERROR READING FILE: {e}\n')
            out.write('\n\n')

def main():
    parser = argparse.ArgumentParser(
        description='프로젝트 폴더 내 소스 파일(.py, .html, .js 등)을 하나의 TXT로 합치기'
    )
    parser.add_argument(
        'root_dir',
        help='프로젝트 최상위 폴더 경로'
    )
    parser.add_argument(
        '-o', '--output',
        default='all_sources.txt',
        help='생성할 TXT 파일명 (기본: all_sources.txt)'
    )
    parser.add_argument(
        '-e', '--extensions',
        nargs='+',
        default=['.py', '.html'],
        help='포함할 파일 확장자 리스트 (예: .py .html .js)'
    )
    parser.add_argument(
        '-x', '--exclude-dirs',
        nargs='*',
        default=['.git', '.venv', '__pycache__', 'migrations'],
        help='탐색에서 제외할 디렉터리 리스트'
    )
    parser.add_argument(
        '-f', '--exclude-files',
        nargs='*',
        default=['manage.py', 'admin.py','apps.py', '__init__.py','tests.py','settings.py'],
        help='제외할 파일 이름 또는 경로 리스트 (스크립트 자신은 자동 제외됨)'
    )

    args = parser.parse_args()

    files = collect_source_files(args.root_dir, args.extensions, args.exclude_dirs, args.exclude_files)
    print(f'총 {len(files)}개 파일을 발견했습니다.')
    write_to_txt(files, args.output)
    print(f'모든 소스가 {args.output} 에 기록되었습니다.')

if __name__ == '__main__':
    main()