import os
import json
import struct

def extract_asar(asar_path, extract_dir):
    os.makedirs(extract_dir, exist_ok=True)
    with open(asar_path, 'rb') as f:
        u1, u2, u3, u4 = struct.unpack('<IIII', f.read(16))
        header_json = f.read(u4).decode('utf-8')
        header = json.loads(header_json)
        base_offset = 8 + u2

        def extract_node(node, current_path):
            files = node.get('files', {})
            for name, item in files.items():
                target = os.path.join(current_path, name)
                if 'files' in item:
                    os.makedirs(target, exist_ok=True)
                    extract_node(item, target)
                else:
                    offset = int(item['offset'])
                    size = int(item['size'])
                    f.seek(base_offset + offset)
                    data = f.read(size)
                    with open(target, 'wb') as out_f:
                        out_f.write(data)

        extract_node(header, extract_dir)

def pack_asar(source_dir, asar_path):
    files_list = []
    
    def scan_dir(dir_path):
        entries = sorted(os.listdir(dir_path))
        node = {'files': {}}
        for entry in entries:
            full_path = os.path.join(dir_path, entry)
            if os.path.isdir(full_path):
                node['files'][entry] = scan_dir(full_path)
            else:
                size = os.path.getsize(full_path)
                files_list.append((full_path, size))
                node['files'][entry] = {'size': size, 'offset': ''}
        return node

    header_dict = scan_dir(source_dir)
    
    current_offset = 0
    file_idx = 0
    def assign_offsets(node):
        nonlocal current_offset, file_idx
        for name, item in node['files'].items():
            if 'files' in item:
                assign_offsets(item)
            else:
                item['offset'] = str(current_offset)
                current_offset += item['size']
                file_idx += 1

    assign_offsets(header_dict)
    
    header_json = json.dumps(header_dict, separators=(',', ':')).encode('utf-8')
    header_len = len(header_json)
    
    # 4-byte alignment padding
    pad_len = (4 - (header_len % 4)) % 4
    header_padded = header_json + (b'\0' * pad_len)
    aligned_header_len = len(header_padded)
    
    u1 = 4
    u2 = aligned_header_len + 8
    u3 = aligned_header_len + 4
    u4 = header_len
    
    with open(asar_path, 'wb') as out_f:
        out_f.write(struct.pack('<IIII', u1, u2, u3, u4))
        out_f.write(header_padded)
        for full_path, size in files_list:
            with open(full_path, 'rb') as in_f:
                # copy in chunks
                while True:
                    chunk = in_f.read(1024 * 1024)
                    if not chunk:
                        break
                    out_f.write(chunk)

if __name__ == '__main__':
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, 'src')
        os.makedirs(os.path.join(src, 'sub'))
        with open(os.path.join(src, 'a.txt'), 'w') as f:
            f.write('Hello World')
        with open(os.path.join(src, 'sub', 'b.txt'), 'w') as f:
            f.write('Sub directory file')
        
        test_asar = os.path.join(td, 'test.asar')
        pack_asar(src, test_asar)
        
        dest = os.path.join(td, 'dest')
        extract_asar(test_asar, dest)
        
        with open(os.path.join(dest, 'a.txt')) as f:
            assert f.read() == 'Hello World'
        with open(os.path.join(dest, 'sub', 'b.txt')) as f:
            assert f.read() == 'Sub directory file'
        print('ASAR pack and extract test PASSED!')
