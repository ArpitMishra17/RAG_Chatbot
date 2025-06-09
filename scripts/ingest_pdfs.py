import os
import psycopg2
from dotenv import load_dotenv
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
import json
from pathlib import Path

# Load environment variables
load_dotenv()

def get_db_connection():
    """Create and return database connection"""
    conn_params = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    }
    return psycopg2.connect(**conn_params)

def chunk_text(text, chunk_size=500, overlap=100):
    """Split text into overlapping chunks"""
    if not text or not text.strip():
        return []
    
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        
        # Ensure chunk has meaningful content
        if chunk.strip():
            chunks.append(chunk.strip())
        
        if end >= len(words):
            break
            
        start += (chunk_size - overlap)
    
    return chunks

def chunk_text_with_tables(text, chunk_size=500, overlap=100):
    """Split text into overlapping chunks while preserving table structure"""
    if not text or not text.strip():
        return []
    
    import re
    
    # More precise table detection - look for actual markdown table patterns
    # This pattern looks for lines with multiple | characters and table headers
    table_patterns = [
        r'(\n\s*\|[^|\n]*\|[^|\n]*\|[^\n]*\n\s*\|[-\s:]+\|[-\s:]+\|[^\n]*\n(?:\s*\|[^|\n]*\|[^|\n]*\|[^\n]*\n)*)',  # Markdown tables with headers
        r'(\n(?:\s*\|[^|\n]+\|[^|\n]+\|[^|\n]*\n){3,})',  # Tables with 3+ rows
    ]
    
    # Find all table matches
    table_matches = []
    for pattern in table_patterns:
        for match in re.finditer(pattern, text, re.MULTILINE):
            table_matches.append((match.start(), match.end(), match.group(1)))
    
    # Sort by position and merge overlapping matches
    table_matches.sort(key=lambda x: x[0])
    merged_tables = []
    for start, end, content in table_matches:
        if merged_tables and start <= merged_tables[-1][1]:
            # Merge overlapping tables
            merged_tables[-1] = (merged_tables[-1][0], max(end, merged_tables[-1][1]), 
                                merged_tables[-1][2] + content)
        else:
            merged_tables.append((start, end, content))
    
    chunks = []
    last_pos = 0
    
    for table_start, table_end, table_content in merged_tables:
        # Add text before table
        before_table = text[last_pos:table_start].strip()
        if before_table:
            chunks.extend(chunk_text(before_table, chunk_size, overlap))
        
        # Process table - keep entire table together if possible
        table_text = table_content.strip()
        
        # Add context before and after table
        context_before = text[max(0, table_start-300):table_start].strip()
        context_after = text[table_end:min(len(text), table_end+300)].strip()
        
        # Create table chunk with context
        table_chunk = ""
        if context_before:
            table_chunk += f"CONTEXT: ...{context_before[-200:]}\n\n"
        
        table_chunk += f"TABLE DATA:\n{table_text}"
        
        if context_after:
            table_chunk += f"\n\nCONTINUED: {context_after[:200]}..."
        
        # If table is very large, split it by rows while preserving headers
        if len(table_chunk.split()) > chunk_size * 1.5:
            table_lines = table_text.split('\n')
            header_lines = []
            data_lines = []
            
            # Find header and separator lines
            for i, line in enumerate(table_lines):
                if line.strip() and '|' in line:
                    if i < 3 or re.match(r'\s*\|[-\s:]+\|', line):  # Header or separator
                        header_lines.append(line)
                    else:
                        data_lines.append(line)
            
            # Create chunks with headers repeated
            if header_lines and data_lines:
                rows_per_chunk = max(5, (chunk_size * 2) // len(header_lines))
                
                for i in range(0, len(data_lines), rows_per_chunk):
                    chunk_rows = data_lines[i:i + rows_per_chunk]
                    table_section = '\n'.join(header_lines + chunk_rows)
                    
                    section_chunk = f"TABLE DATA (Part {i//rows_per_chunk + 1}):\n{table_section}"
                    if context_before and i == 0:
                        section_chunk = f"CONTEXT: ...{context_before[-200:]}\n\n" + section_chunk
                    
                    chunks.append(section_chunk)
            else:
                chunks.append(table_chunk)
        else:
            chunks.append(table_chunk)
        
        last_pos = table_end
    
    # Add remaining text after last table
    remaining_text = text[last_pos:].strip()
    if remaining_text:
        chunks.extend(chunk_text(remaining_text, chunk_size, overlap))
    
    # If no tables found, use regular chunking
    if not merged_tables:
        return chunk_text(text, chunk_size, overlap)
    
    return [chunk.strip() for chunk in chunks if chunk.strip()]

def ingest_pdfs():
    """Extract and ingest PDFs into database using Docling"""
    # Determine the absolute path to the project's root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    pdf_dir = project_root / "data" / "pdfs"
    
    print(f"Looking for PDFs in: {pdf_dir}")
    
    if not pdf_dir.exists():
        print(f"PDF directory {pdf_dir} does not exist!")
        print("Please create the directory and add PDF files to process.")
        return
    
    pdf_files = [f for f in pdf_dir.iterdir() if f.suffix.lower() == '.pdf']
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    # Initialize Docling converter with better pipeline options
    try:
        # Configure pipeline options for better extraction
        pipeline_options = PdfPipelineOptions(
            do_ocr=True,  # Enable OCR for scanned documents
            do_table_structure=True,  # Enable table structure recognition
        )
        
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        print("Docling converter initialized successfully!")
    except Exception as e:
        print(f"Error initializing Docling converter: {e}")
        print("Falling back to basic converter...")
        try:
            converter = DocumentConverter()
            print("Basic Docling converter initialized!")
        except Exception as e2:
            print(f"Failed to initialize any converter: {e2}")
            return
    
    conn = None
    cur = None
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        print("Database connection established!")
        
        processed_count = 0
        
        for pdf_file in pdf_files:
            filename = pdf_file.name
            
            try:
                print(f"\nProcessing {filename}...")
                
                # Check if file already processed
                cur.execute("SELECT id FROM documents WHERE source_name = %s", (filename,))
                existing_doc = cur.fetchone()
                
                if existing_doc:
                    print(f"  - {filename} already processed (ID: {existing_doc[0]}), skipping...")
                    continue
                
                # Process PDF with Docling
                print(f"  - Converting PDF with Docling...")
                result = converter.convert(str(pdf_file))
                
                if not result or not result.document:
                    print(f"  - No document result from Docling for {filename}")
                    continue
                
                # Method 1: Try to get markdown export (most comprehensive)
                try:
                    raw_text = result.document.export_to_markdown()
                    print(f"  - Extracted text using markdown export (length: {len(raw_text)})")
                except Exception as e:
                    print(f"  - Markdown export failed: {e}")
                    raw_text = ""
                
                # Method 2: If markdown export fails, try export_to_text
                if not raw_text.strip():
                    try:
                        raw_text = result.document.export_to_text()
                        print(f"  - Extracted text using text export (length: {len(raw_text)})")
                    except Exception as e:
                        print(f"  - Text export failed: {e}")
                        raw_text = ""
                
                # Method 3: If both exports fail, try accessing document structure directly
                if not raw_text.strip():
                    try:
                        text_parts = []
                        
                        # Try to access document body
                        if hasattr(result.document, 'body') and result.document.body:
                            for element in result.document.body:
                                if hasattr(element, 'text') and element.text:
                                    text_parts.append(element.text.strip())
                        
                        # Try to access document texts
                        if hasattr(result.document, 'texts') and result.document.texts:
                            for text_element in result.document.texts:
                                if hasattr(text_element, 'text') and text_element.text:
                                    text_parts.append(text_element.text.strip())
                        
                        raw_text = "\n\n".join(text_parts)
                        print(f"  - Extracted text using direct access (length: {len(raw_text)})")
                        
                    except Exception as e:
                        print(f"  - Direct access failed: {e}")
                        raw_text = ""
                
                # Method 4: Last resort - try to convert to dict and extract text
                if not raw_text.strip():
                    try:
                        doc_dict = result.document.export_to_dict()
                        text_parts = []
                        
                        def extract_text_recursive(obj):
                            if isinstance(obj, dict):
                                if 'text' in obj and obj['text']:
                                    text_parts.append(str(obj['text']).strip())
                                for value in obj.values():
                                    extract_text_recursive(value)
                            elif isinstance(obj, list):
                                for item in obj:
                                    extract_text_recursive(item)
                        
                        extract_text_recursive(doc_dict)
                        raw_text = "\n\n".join(text_parts)
                        print(f"  - Extracted text using recursive dict parsing (length: {len(raw_text)})")
                        
                    except Exception as e:
                        print(f"  - Recursive dict parsing failed: {e}")
                        raw_text = ""
                
                if not raw_text.strip():
                    print(f"  - No text extracted from {filename}, skipping...")
                    continue
                
                # Clean up the text
                raw_text = raw_text.strip()
                
                # Insert document
                cur.execute(
                    "INSERT INTO documents (source_name, raw_text) VALUES (%s, %s) RETURNING id;",
                    (filename, raw_text)
                )
                doc_id = cur.fetchone()[0]
                
                # Chunk the text
                chunks = chunk_text_with_tables(raw_text, chunk_size=600, overlap=150)  # Larger chunks for tables
                print(f"  - Created {len(chunks)} chunks")
                
                if not chunks:
                    print(f"  - No chunks created for {filename}")
                    # Delete the document record since we couldn't create chunks
                    cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                    continue
                
                # Insert chunks
                for idx, chunk in enumerate(chunks):
                    cur.execute(
                        """
                        INSERT INTO doc_chunks (doc_id, chunk_index, chunk_text, embedding)
                        VALUES (%s, %s, %s, NULL);
                        """,
                        (doc_id, idx, chunk)
                    )
                
                conn.commit()
                processed_count += 1
                print(f"  - Successfully processed {filename} (Document ID: {doc_id})")
                
                # Show a sample of the extracted text
                sample_text = raw_text[:200] + "..." if len(raw_text) > 200 else raw_text
                print(f"  - Sample text: {sample_text}")
                
            except Exception as e:
                print(f"  - Error processing {filename}: {e}")
                if conn:
                    conn.rollback()
                continue
        
        print(f"\nPDF ingestion completed! Successfully processed {processed_count}/{len(pdf_files)} files.")
        
        # Show summary
        cur.execute("SELECT COUNT(*) FROM documents;")
        total_docs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM doc_chunks;")
        total_chunks = cur.fetchone()[0]
        
        print(f"Database summary:")
        print(f"  - Total documents: {total_docs}")
        print(f"  - Total chunks: {total_chunks}")
        
        # Show some sample data
        if total_docs > 0:
            print(f"\nSample documents:")
            cur.execute("SELECT id, source_name, LENGTH(raw_text) FROM documents ORDER BY id LIMIT 3;")
            for doc_id, source_name, text_length in cur.fetchall():
                print(f"  - ID {doc_id}: {source_name} ({text_length} characters)")
        
    except Exception as e:
        print(f"Critical error during PDF ingestion: {e}")
        if conn:
            conn.rollback()
        raise
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    ingest_pdfs()