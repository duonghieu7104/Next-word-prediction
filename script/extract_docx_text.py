#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để extract text từ các file docx trong thư mục data/raw/docx
và chuẩn bị dữ liệu cho mô hình dự đoán từ tiếp theo
"""

import os
import re
from pathlib import Path
from docx import Document
import pandas as pd
from typing import List, Dict, Tuple
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocxTextExtractor:
    def __init__(self, input_dir: str, output_dir: str):
        """
        Khởi tạo extractor
        
        Args:
            input_dir: Thư mục chứa file docx
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
    
    def extract_text_from_docx(self, docx_path: Path) -> str:
        """
        Extract text từ file docx
        
        Args:
            docx_path: Đường dẫn đến file docx
            
        Returns:
            Text đã extract và làm sạch
        """
        try:
            doc = Document(docx_path)
            full_text = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    full_text.append(paragraph.text.strip())
            
            # Nối tất cả text lại
            text = '\n'.join(full_text)
            
            # Làm sạch text
            cleaned_text = self.clean_text(text)
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Lỗi khi đọc file {docx_path}: {str(e)}")
            return ""
    
    def process_all_docx_files(self) -> Dict[str, str]:
        """
        Xử lý tất cả file docx trong thư mục input
        
        Returns:
            Dictionary với key là tên file và value là text content
        """
        docx_files = list(self.input_dir.glob("*.docx"))
        logger.info(f"Tìm thấy {len(docx_files)} file docx")
        
        extracted_texts = {}
        
        for docx_file in docx_files:
            logger.info(f"Đang xử lý: {docx_file.name}")
            
            text = self.extract_text_from_docx(docx_file)
            
            if text:
                extracted_texts[docx_file.stem] = text
                logger.info(f"Đã extract {len(text)} ký tự từ {docx_file.name}")
            else:
                logger.warning(f"Không thể extract text từ {docx_file.name}")
        
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
        combined_file = self.output_dir / "combined_novel_text.txt"
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
        metadata_file = self.output_dir / "metadata.csv"
        df.to_csv(metadata_file, index=False, encoding='utf-8')
        
        logger.info(f"Đã tạo file metadata: {metadata_file}")
        
        # In thống kê tổng quan
        total_chars = df['character_count'].sum()
        total_words = df['word_count'].sum()
        total_files = len(df)
        
        logger.info(f"Thống kê tổng quan:")
        logger.info(f"- Tổng số file: {total_files}")
        logger.info(f"- Tổng số ký tự: {total_chars:,}")
        logger.info(f"- Tổng số từ: {total_words:,}")
        logger.info(f"- Trung bình ký tự/file: {total_chars/total_files:,.0f}")
        logger.info(f"- Trung bình từ/file: {total_words/total_files:,.0f}")

def main():
    """Hàm chính để chạy quá trình extract text"""
    
    # Đường dẫn thư mục
    input_dir = "data/raw/docx"
    output_dir = "data/clean"
    
    # Tạo extractor
    extractor = DocxTextExtractor(input_dir, output_dir)
    
    logger.info("Bắt đầu quá trình extract text từ file docx...")
    
    # Extract text từ tất cả file docx
    extracted_texts = extractor.process_all_docx_files()
    
    if not extracted_texts:
        logger.error("Không thể extract text từ bất kỳ file nào!")
        return
    
    # Lưu text vào các file riêng biệt
    extractor.save_extracted_texts(extracted_texts)
    
    # Tạo dataset tổng hợp
    combined_file = extractor.create_combined_dataset(extracted_texts)
    
    # Tạo metadata
    extractor.create_metadata(extracted_texts)
    
    logger.info("Hoàn thành quá trình extract text!")

if __name__ == "__main__":
    main()
