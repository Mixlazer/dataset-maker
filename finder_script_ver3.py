import Metashape
from PySide2.QtWidgets import QDialog
import shapely.speedups
from shapely.geometry import Polygon, Point
from osgeo import gdal, gdalconst
from typing import List
from PIL import Image
import random
import os
import glob
import shutil

class core:
    class Vector:
        def __init__(self, coordinates: List[float]):
            self.x = coordinates[0]
            self.y = coordinates[1]

    # функция для преобразования кортежей в yolo-like формат (отстутвует нормализация)
    def convert_tuples_to_yolo_obb(tuples: List[tuple[float, float]], class_index: int = 15) -> str:
        if len(tuples) != 4 and len(tuples) != 5:
            raise ValueError("Полигон должен содержать ровно 4 или 5 вершин (включая дублирующую первую).")
        if len(tuples) == 5 and tuples[0] == tuples[-1]:
            tuples = tuples[:-1]
        result = f"{class_index} "
        for x, y in tuples:
            result += f"{x} {y} "
        result = result.rstrip(',')
        return result

    def create_and_append_to_file(file_name, line):
        try:
            # Открываем файл в режиме добавления (append). Если файл не существует, он будет создан.
            with open(file_name, 'a', encoding='utf-8') as file:
                file.write(line + '\n')

        except Exception as e:
            print(f"Произошла ошибка при работе с файлом: {e}")

    def convert_vectors_to_tuples(vectors: List['core.Vector']) -> List[tuple[float, float]]:
        return [(vector.x, vector.y) for vector in vectors]

    # Функция для трансформации обычного полигона в наклонный(obb)
    def rectilinear_partitioning(points):
        polygon = Polygon(points)
        rectangles = list(polygon.minimum_rotated_rectangle.exterior.coords)
        return rectangles

    def get_tile_coordinates(tiff_file):
        try:
            # Открытие изображения с помощью GDAL
            dataset = gdal.Open(tiff_file)
            if not dataset:
                raise ValueError("Нельзя открыть при помощи GDAL")

            # Проверка на наличие геопривязки
            geo_transform = dataset.GetGeoTransform()
            if geo_transform:
                x_min = geo_transform[0]
                y_max = geo_transform[3]
                x_res = geo_transform[1]
                y_res = geo_transform[5]

                x_max = x_min + (dataset.RasterXSize * x_res)
                y_min = y_max + (dataset.RasterYSize * y_res)

                coordinates = (x_min, y_max, x_max, y_max, x_max, y_min, x_min, y_min)
            else:
                # Если геопривязка отсутствует, используем размеры изображения
                with Image.open(tiff_file) as img:
                    width, height = img.size
                    coordinates = (0, 0, width, 0, width, height, 0, height)

            return coordinates

        except (IOError, SyntaxError, ValueError) as e:
            print(f"Ошибка при открытии {tiff_file}: {e}")
            return None

    # Запись параметров тайлов исключая маски в name_and_coords_of_tile.txt
    def exclude_masks(folder_path):
        # Открытие файла для записи
        with open("name_and_coords_of_tile.txt", "w") as output_file:
            files = [f for f in os.listdir(folder_path) if (f.lower().endswith('.tiff') or f.lower().endswith('.tif')) and not f.lower().endswith('-p.tif') and not f.lower().endswith('-p.tiff') and f.lower().count('l') < 2]
            for file in files:
                file_path = os.path.join(folder_path, file)
                coordinates = core.get_tile_coordinates(file_path)
                if coordinates:
                    output_file.write(f"{file}: {coordinates}\n")
                    output_file.write("\n")

    # Считываем полигоны
    def read_polygons(file_path):
        polygons = []
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 9:
                    print(f"Ошибка считывания следующего полигона: {line}")
                    continue
                class_id = parts[0]
                coords = list(map(float, parts[1:]))
                polygon_points = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                polygons.append((class_id, polygon_points))
        return polygons

    # Считываем тайлы
    def read_tiles(file_path):
        tiles = []
        with open(file_path, 'r') as f:
            for line in f:
                if ': ' not in line:
                    print(f"Пропуск тайла: {line}")
                    continue
                name, coords_str = line.split(': ', 1)
                coords = list(map(float, coords_str.strip('()\n').split(', ')))
                if len(coords) != 8:
                    print(f"Пропуск тайла с неподходящими координатами: {line}")
                    continue
                tile_points = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                tiles.append((name, tile_points))
        return tiles

    # Проверка на наличие какой-либо точки полигона внутри тайла
    def is_point_in_tile(point, tile_polygon):
        return tile_polygon.contains(Point(point))

    def process_files(polygons_file, tiles_file, output_file):
        polygons = core.read_polygons(polygons_file)
        tiles = core.read_tiles(tiles_file)

        with open(output_file, 'w') as f:
            for tile_name, tile_points in tiles:
                tile_polygon = Polygon(tile_points)
                for class_id, polygon_points in polygons:
                    if any(core.is_point_in_tile(point, tile_polygon) for point in polygon_points):
                        coords_str = ' '.join(f'{x} {y}' for x, y in polygon_points)
                        f.write(f'{tile_name}: {class_id}, {coords_str}\n')

    # Функция преобразования tif файла в png(маски создаваемые при появлении ортомозаика не рассматриваем)
    def convert_tif_to_png(input_folder, scale=4096):
        files = [os.path.join(input_folder, f) for f in os.listdir(input_folder) if f.lower().endswith('.tif') and not f.lower().endswith('-p.tif') and f.lower().count('l') < 2]
        png_files = []
        for file in files:
            try:
                gdal_dataset = gdal.Open(file)
                if gdal_dataset is None:
                    print(f"Пропуск файла {file} - GDAL не смог открыть файл")
                    continue

                png_file = os.path.splitext(file)[0] + '.png'
                gdal.Translate(png_file, gdal_dataset, format='PNG', width=scale, height=scale)
                png_files.append(png_file)
            except Exception as e:
                print(f"Пропуск файла: {file} - Ошибка: {e}")

        return png_files

    # Функция для распределения количества png файлов в train test val в зависимости от введенного процентного соотношения
    def split_files(files, percentages):
        total_files = len(files)
        test_count = int(total_files * percentages[0] / 100)
        train_count = int(total_files * percentages[1] / 100)
        val_count = total_files - train_count - test_count

        random.shuffle(files)

        train_files = files[:train_count]
        test_files = files[train_count:train_count + test_count]
        val_files = files[train_count + test_count:]

        return train_files, test_files, val_files

    # Создание папок
    def create_directories(base_dir):
        images_dir = os.path.join(base_dir, 'images')
        labels_dir = os.path.join(base_dir, 'labels')

        os.makedirs(os.path.join(images_dir, 'train'), exist_ok=True)
        os.makedirs(os.path.join(images_dir, 'test'), exist_ok=True)
        os.makedirs(os.path.join(images_dir, 'val'), exist_ok=True)
        os.makedirs(os.path.join(labels_dir, 'train'), exist_ok=True)
        os.makedirs(os.path.join(labels_dir, 'test'), exist_ok=True)
        os.makedirs(os.path.join(labels_dir, 'val'), exist_ok=True)

        return (os.path.join(images_dir, 'train'), os.path.join(images_dir, 'test'), os.path.join(images_dir, 'val'),
                os.path.join(labels_dir, 'train'), os.path.join(labels_dir, 'test'), os.path.join(labels_dir, 'val'))

    def copy_files_and_delete_source(files, dest_dir):
        for file in files:
            try:
                shutil.copy(file, dest_dir)
                os.remove(file)
            except Exception as e:
                print(f"Ошибка в удалении файлов {file} - {e}")

    def main(input_folder, scale, percentages, results_path):
        png_files = core.convert_tif_to_png(input_folder, scale)

        if not png_files:
            print("Не было создано ни одного Png файла")
            return

        test_images_dir, train_images_dir, val_images_dir, test_labels_dir, train_labels_dir, val_labels_dir = core.create_directories(results_path)
        test_files, train_files, val_files = core.split_files(png_files, percentages)
        core.copy_files_and_delete_source(train_files, train_images_dir)
        core.copy_files_and_delete_source(test_files, test_images_dir)
        core.copy_files_and_delete_source(val_files, val_images_dir)

    # Функция для чтения файла и преобразования его содержимого в словарь
    def read_tile_coordinates(filename):
        with open(filename, 'r') as file:
            tile_data = {}
            for line in file:
                if ': ' in line:
                    tile_name, coords = line.strip().split(': ')
                    coords = eval(coords)
                    tile_data[tile_name] = coords
            return tile_data

    # Функция для чтения detected файла и преобразования его содержимого в список
    def read_detected(filename):
        with open(filename, 'r') as file:
            detected_data = []
            for line in file:
                if ': ' in line:
                    tile_name, data = line.strip().split(': ')
                    class_index, *coords = data.split(', ')
                    coords = list(map(float, ' '.join(coords).split()))
                    detected_data.append((tile_name, int(class_index), coords))
            return detected_data

    # Нормализация координат полигона относительно границ тайла
    def normalize_coords(coords, tile_coords):
        x_min = min(tile_coords[::2])
        x_max = max(tile_coords[::2])
        y_min = min(tile_coords[1::2])
        y_max = max(tile_coords[1::2])

        normalized = []
        for i in range(0, len(coords), 2):
            x = (coords[i] - x_min) / (x_max - x_min)
            y = (coords[i + 1] - y_min) / (y_max - y_min)
            normalized.extend([x, y])
        return normalized

    def extract_data(filename, image_filename):
        with open(filename, 'r') as f:
            lines = f.readlines()
        data_lines = [line.strip().split(': ')[1] for line in lines if line.startswith(image_filename)]

        return data_lines

    # Создание лейблов соответсвующих каждому png файлу
    def create_label_files(image_folder, label_folder, doc_path):
        png_files = glob.glob(os.path.join(image_folder, '*.png'))

        for png_file in png_files:
            filename = os.path.basename(png_file)
            image_filename = os.path.splitext(filename)[0]
            label_filename = os.path.join(label_folder, image_filename + '.txt')
            data = core.extract_data(doc_path+'/'+"normalized_coordinates.txt", image_filename)
            unique_data = set(data)

            with open(label_filename, 'w') as f:
                for line in unique_data:
                    if line.startswith(image_filename + ': '):
                        line = line[len(image_filename) + 2:]
                    f.write(line + '\n')

    # Удаление временных файлов возникающих при трансформации tif в png
    def delete_xml_and_msk_files(folder_path):
        try:
            files = os.listdir(folder_path)
            for file in files:
                if file.endswith('.xml') or file.endswith('.msk'):
                    file_path = os.path.join(folder_path, file)
                    os.remove(file_path)
        except Exception as e:
            print(f"Ошибка в удалении файлов: {e}")

    # удаляем временные файлы
    def delete_temp_files(document_path):
        try:
            os.remove(document_path+'/'+'polygons.txt')
            os.remove(document_path+'/'+'name_and_coords_of_tile.txt')
            os.remove(document_path+'/'+'detected1.txt')
            os.remove(document_path+'/'+'normalized_coordinates.txt')
        except Exception as e:
            print(f"Ошибка в удалении файлов: {e}")

    @staticmethod
    def process_metashape_data(layer_name, results_folder, percentages, scale):
        doc = Metashape.app.document
        chunk = doc.chunk
        # записываем путь к директории проверяя открыта ли сцена
        if doc:
            scene_path = doc.path
            doc_path = os.path.dirname(scene_path)
            folder_path = scene_path[:-4] + '.files' + '/0/0/orthomosaic'
            print(f"Metashape: {doc_path}")
        else:
            print("Нет открытой сцены в Metashape.")
            return

        shapely.speedups.disable()

        class_mapping = {
            'plane': 0,
            'ship': 1,
            'storage tank': 2,
            'baseball diamond': 3,
            'tennis court': 4,
            'basketball court': 5,
            'ground track field': 6,
            'harbor': 7,
            'bridge': 8,
            'large vehicle': 9,
            'small vehicle': 10,
            'helicopter': 11,
            'roundabout': 12,
            'soccer ball field': 13,
            'swimming pool': 14,
            'not found': 15
        }

        selected_shape_layer = [shape for shape in chunk.shapes if shape.group.label == layer_name]
        # Чтение фигур полигонов и их ограничивающих рамок
        for shape in selected_shape_layer:
            exterior_ring = shape.geometry.coordinates
            vertices = [vertex for vertex in exterior_ring]
            for vertex in vertices:
                print(vertex)
                converted_tupples = core.convert_vectors_to_tuples(vertex)[:-1]
                print(core.convert_tuples_to_yolo_obb(converted_tupples))
                points = [Point(coord) for coord in converted_tupples]
                print(points)
                x = ''
                for point in points:
                    print(point.x, point.y)
                poly = shapely.geometry.Polygon([[p.x, p.y] for p in points])
                print(core.rectilinear_partitioning(points))
                print(class_mapping.get(shape.attributes['class'], 15))
                x = x + core.convert_tuples_to_yolo_obb(core.rectilinear_partitioning(points), class_mapping.get(shape.attributes['class'], 15))
                core.create_and_append_to_file('polygons.txt', x)

        core.exclude_masks(folder_path)
        polygons_file = 'polygons.txt'
        tiles_file = 'name_and_coords_of_tile.txt'
        output_file = 'detected1.txt'
        core.process_files(polygons_file, tiles_file, output_file)
        core.main(folder_path, scale, percentages, results_folder)
        # Прочитать данные из файлов
        tile_coordinates = core.read_tile_coordinates('name_and_coords_of_tile.txt')
        detected_data = core.read_detected('detected1.txt')
        # Записываем нормализованные данные в файл
        output_filepath = 'normalized_coordinates.txt'
        with open(output_filepath, 'w') as output_file:
            for tile_name, class_index, coords in detected_data:
                tile_coords = tile_coordinates[tile_name]
                normalized_coords = core.normalize_coords(coords, tile_coords)
                normalized_coords_str = ', '.join(map(str, normalized_coords))
                output_file.write(f'{tile_name}: {class_index}, {normalized_coords_str}\n')

        print(f"Нормализованные данные успешно записаны в {output_filepath}")

        for split in ['test', 'train', 'val']:
            image_folder = os.path.join(results_folder, 'images', split)
            label_folder = os.path.join(results_folder, 'labels', split)
            os.makedirs(label_folder, exist_ok=True)
            core.create_label_files(image_folder, label_folder, doc_path)

        core.delete_xml_and_msk_files(folder_path)
        core.delete_temp_files(doc_path)
        doc.save()


