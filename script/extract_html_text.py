#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để extract text từ các file HTML trong thư mục data/raw/htm
và chuẩn bị dữ liệu cho mô hình dự đoán từ tiếp theo
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict, Tuple
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HtmlTextExtractor:
    def __init__(self, input_dir: str, output_dir: str):
        """
        Khởi tạo extractor
        
        Args:
            input_dir: Thư mục chứa file HTML
            output_dir: Thư mục lưu text đã extract
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def clean_text(self, text: str) -> str:
        """
        Làm sạch text: loại bỏ ký tự đặc biệt không cần thiết, chuẩn hóa khoảng trắng
        
        Args:
            text: Text cần làm sạch
            
        Returns:
            Text đã được làm sạch
        """
        # Loại bỏ ký tự đặc biệt không cần thiết nhưng giữ lại dấu câu quan trọng
        text = re.sub(r'[^\w\s\u00C0-\u1EF9\u1EA0-\u1EF9.,!?;:()""''…]', ' ', text)
        
        # Chuẩn hóa khoảng trắng nhưng giữ nguyên dấu câu
        text = re.sub(r'\s+', ' ', text)
        
        # Loại bỏ khoảng trắng đầu và cuối
        text = text.strip()
        
        return text
    
    def extract_text_from_html(self, html_path: Path) -> str:
        """
        Extract text từ file HTML
        
        Args:
            html_path: Đường dẫn đến file HTML
            
        Returns:
            Text đã extract và làm sạch
        """
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Sử dụng BeautifulSoup để parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Loại bỏ các thẻ script và style
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Tìm nội dung chính trong thẻ article
            article = soup.find('article')
            
            if article:
                # Lấy tất cả thẻ p trong article
                paragraphs = article.find_all('p')
                text_parts = []
                
                for p in paragraphs:
                    # Lấy text từ thẻ p và làm sạch
                    p_text = p.get_text().strip()
                    if p_text:  # Chỉ thêm nếu có nội dung
                        text_parts.append(p_text)
                
                # Nối các đoạn văn lại
                text = '\n'.join(text_parts)
            else:
                # Nếu không tìm thấy article, thử tìm div story-content
                story_content = soup.find('div', class_='story-content')
                if story_content:
                    text = story_content.get_text()
                else:
                    # Fallback: lấy toàn bộ text từ body
                    body = soup.find('body')
                    if body:
                        text = body.get_text()
                    else:
                        text = soup.get_text()
            
            # Làm sạch text
            cleaned_text = self.clean_text(text)
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Lỗi khi đọc file {html_path}: {str(e)}")
            return ""
    
    def process_all_html_files(self) -> Dict[str, str]:
        """
        Xử lý tất cả file HTML trong thư mục input và các thư mục con
        
        Returns:
            Dictionary với key là tên file và value là text content
        """
        # Tìm tất cả file HTML trong thư mục và các thư mục con
        html_files = list(self.input_dir.rglob("*.htm")) + list(self.input_dir.rglob("*.html"))
        logger.info(f"Tìm thấy {len(html_files)} file HTML")
        
        extracted_texts = {}
        
        for html_file in html_files:
            logger.info(f"Đang xử lý: {html_file.name}")
            
            text = self.extract_text_from_html(html_file)
            
            if text:
                # Tạo tên file unique bằng cách kết hợp tên thư mục và file
                relative_path = html_file.relative_to(self.input_dir)
                file_key = str(relative_path).replace('\\', '_').replace('/', '_').replace('.htm', '').replace('.html', '')
                
                extracted_texts[file_key] = text
                logger.info(f"Đã extract {len(text)} ký tự từ {html_file.name}")
            else:
                logger.warning(f"Không thể extract text từ {html_file.name}")
        
        return extracted_texts
    
    def save_extracted_texts(self, extracted_texts: Dict[str, str]):
        """
        Lưu text đã extract vào các file riêng biệt
        
        Args:
            extracted_texts: Dictionary chứa text đã extract
        """
        for filename, text in extracted_texts.items():
            output_file = self.output_dir / f"{filename}.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            logger.info(f"Đã lưu text vào {output_file}")
    
    def create_combined_dataset(self, extracted_texts: Dict[str, str]) -> str:
        """
        Tạo dataset tổng hợp từ tất cả text
        
        Args:
            extracted_texts: Dictionary chứa text đã extract
            
        Returns:
            Đường dẫn đến file dataset tổng hợp
        """
        # Nối tất cả text lại
        all_text = []
        
        for filename, text in extracted_texts.items():
            all_text.append(f"=== {filename} ===\n{text}\n")
        
        combined_text = '\n'.join(all_text)
        
        # Lưu file tổng hợp
        combined_file = self.output_dir / "combined_html_novel_text.txt"
        with open(combined_file, 'w', encoding='utf-8') as f:
            f.write(combined_text)
        
        logger.info(f"Đã tạo file tổng hợp: {combined_file}")
        return str(combined_file)
    
    def create_metadata(self, extracted_texts: Dict[str, str]):
        """
        Tạo file metadata chứa thông tin về các file đã xử lý
        
        Args:
            extracted_texts: Dictionary chứa text đã extract
        """
        metadata = []
        
        for filename, text in extracted_texts.items():
            metadata.append({
                'filename': filename,
                'character_count': len(text),
                'word_count': len(text.split()),
                'line_count': len(text.split('\n'))
            })
        
        # Tạo DataFrame và lưu
        df = pd.DataFrame(metadata)
        metadata_file = self.output_dir / "html_metadata.csv"
        df.to_csv(metadata_file, index=False, encoding='utf-8')
        
        logger.info(f"Đã tạo file metadata: {metadata_file}")
        
        # In thống kê tổng quan
        total_chars = df['character_count'].sum()
        total_words = df['word_count'].sum()
        total_files = len(df)
        
        logger.info(f"Thống kê tổng quan HTML:")
        logger.info(f"- Tổng số file: {total_files}")
        logger.info(f"- Tổng số ký tự: {total_chars:,}")
        logger.info(f"- Tổng số từ: {total_words:,}")
        logger.info(f"- Trung bình ký tự/file: {total_chars/total_files:,.0f}")
        logger.info(f"- Trung bình từ/file: {total_words/total_files:,.0f}")

def main():
    """Hàm chính để chạy quá trình extract text từ HTML"""
    
    # Đường dẫn thư mục
    input_dir = "data/raw/htm"
    output_dir = "data/clean"
    
    # Tạo extractor
    extractor = HtmlTextExtractor(input_dir, output_dir)
    
    logger.info("Bắt đầu quá trình extract text từ file HTML...")
    
    # Extract text từ tất cả file HTML
    extracted_texts = extractor.process_all_html_files()
    
    if not extracted_texts:
        logger.error("Không thể extract text từ bất kỳ file nào!")
        return
    
    # Lưu text vào các file riêng biệt
    extractor.save_extracted_texts(extracted_texts)
    
    # Tạo dataset tổng hợp
    combined_file = extractor.create_combined_dataset(extracted_texts)
    
    # Tạo metadata
    extractor.create_metadata(extracted_texts)
    
    logger.info("Hoàn thành quá trình extract text từ HTML!")

if __name__ == "__main__":
    main()
