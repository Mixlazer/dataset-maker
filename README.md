# dataset-maker

## Описание

**Создатель датасетов** - плагин, который позволяет в автоматическом порядке преобразовывать различные объекты обведенные 
полигонами на ортофотоплане и части ортофотоплана в датасет. Обнаруженые на выбранном слое полигоны преобразуются в 
ориентированные ограничительные коробки (OBB) они как и части ортофотоплана сохраняются в выбранном месте в формате двух папок images
и lables, в каждом из которых находятся директории test, train и val, соотношение файлов в которых вводится пользователем. 
Внутри images сохряняются части ортофотоплана в png формате, разрешение которого определяется пользователем, внутри lables
сохрянются соответствующие(находящиеся на нем) каждой части ортофотоплана полигоны в формате yolo-obb (class_index, x1, y1, x2, y2, x3, y3, x4, y4).

## Использование

Интерфейс содержит одну страницу. На которой находятся обязательные к указанию параметры
создателя датасетов:

* Слой фигур, с которого будут обработаны полигоны.
* Разрешение изображений, им определяется разрешение созданных png файлов, содержащих части ортофотоплана .
* Соотношение Тестовой/Тренировочной/Валидационной выборок, он определяет количественное соотношение частей ортофотоплана и соответсвующих им фигур 
в папках test, train и val
* Путь к результату, путь где будут сохранены результаты работы плагина.


Изначально во вкладке дополнительно заданы параметры, оптимальные для работы плагина. Для того чтобы корректного исполнения модуля
необходимо заполнить все входные параметры  и запустить работу плагина.

После запуска плагина начнется его поэтапное исполнение. В первую очередь создастся временный файл polygons.txt с считанными и преобразованными в obb координатами полигонов на выбраном слое, далее создается временный файл name_and_coords_of_tile.txt с именами и координатами граничных углов частей ортофотоплана, после этого создается 
detected1.txt где каждому полигону приписывается соответсвующий ему класс (если класс не указан, то он равен 15), далее их координаты нормализуются в границах соответствующей части ортофотоплана и происходит их сохранение в normalized_coordinates.txt, после этого части ортофотоплана и соотвествующие им в normalized_coordinates.txt полигоны сохраняются в выбранной папке.
