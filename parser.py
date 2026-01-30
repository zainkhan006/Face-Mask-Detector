import os
import xml.etree.ElementTree as ET
import statistics
from collections import defaultdict


def parse(xmlPath):
    tree = ET.parse(xmlPath)
    root = tree.getroot()
    filename = root.find('filename').text
    size = root.find('size')
    width = int(size.find('width').text)
    height = int(size.find('height').text)
    faces = []
    for obj in root.findall('object'):
        className = obj.find('name')
        if className is None:
            className = obj.find('n') 
        classLabel = className.text
        
        #bounding box info
        boundBox = obj.find('bndbox')
        xmin = int(boundBox.find('xmin').text)
        ymin = int(boundBox.find('ymin').text)
        xmax = int(boundBox.find('xmax').text)
        ymax = int(boundBox.find('ymax').text)
        
        # bounding box dimensions
        boundBoxWidth = xmax - xmin
        boundBoxHeight = ymax - ymin
        boundBoxArea = boundBoxWidth * boundBoxHeight
        
        truncated = int(obj.find('truncated').text) if obj.find('truncated') is not None else 0
        occluded = int(obj.find('occluded').text) if obj.find('occluded') is not None else 0
        difficult = int(obj.find('difficult').text) if obj.find('difficult') is not None else 0
        
        faces.append({
            'class': classLabel,
            'boundBox': (xmin, ymin, xmax, ymax),
            'boundBoxWidth': boundBoxWidth,
            'boundBoxHeight': boundBoxHeight,
            'boundBoxArea': boundBoxArea,
            'truncated': truncated,
            'occluded': occluded,
            'difficult': difficult
        })
    
    return {
        'filename': filename,
        'width': width,
        'height': height,
        'faces': faces
    }


def analyzeDataset(directory):
    xmlFiles = [f for f in os.listdir(directory) if f.endswith('.xml')]
    totalImages = len(xmlFiles)
    
    print("parsing annotated file: ")

    numberOfClasses = defaultdict(int)
    boundBoxWidths = []
    boundBoxHeights = []
    boundBoxAreas = []
    facesPerImage = []
    
    imagesWithMultipleFaces = 0
    nooftruncatedimages = 0
    noofoccludedimages = 0
    noofdifficultimages = 0
    
    classBoundBoxWidths = defaultdict(list)
    classBoundBoxHeights = defaultdict(list)
    
    imageWidths = []
    imageHeights = []
    
    for xmlFile in xmlFiles:
        xmlpath = os.path.join(directory, xmlFile)
        try:
            imageData = parse(xmlpath)
            imageWidths.append(imageData['width'])
            imageHeights.append(imageData['height'])
            nooffaces = len(imageData['faces'])
            facesPerImage.append(nooffaces)
            
            if nooffaces > 1:
                imagesWithMultipleFaces += 1

            for face in imageData['faces']:
                numberOfClasses[face['class']] += 1
                boundBoxWidths.append(face['boundBoxWidth'])
                boundBoxHeights.append(face['boundBoxHeight'])
                boundBoxAreas.append(face['boundBoxArea'])
                classBoundBoxWidths[face['class']].append(face['boundBoxWidth'])
                classBoundBoxHeights[face['class']].append(face['boundBoxHeight'])
                
                if face['truncated']:
                    nooftruncatedimages += 1
                if face['occluded']:
                    noofoccludedimages += 1
                if face['difficult']:
                    noofdifficultimages += 1
                    
        except Exception as e:
            print(f"error parsing {xmlFile}: {e}")
    
    totalFaces = sum(numberOfClasses.values())
    
    results = {
        'totalImages': totalImages,
        'totalFaces': totalFaces,
        'noOfClasses': dict(numberOfClasses),
        'imagesWithMultipleFaces': imagesWithMultipleFaces,
        'facesPerImage': {
            'mean': statistics.mean(facesPerImage),
            'median': statistics.median(facesPerImage),
            'min': min(facesPerImage),
            'max': max(facesPerImage)
        },
        'imageDimensions': {
            'width': {
                'mean': statistics.mean(imageWidths),
                'min': min(imageWidths),
                'max': max(imageWidths)
            },
            'height': {
                'mean': statistics.mean(imageHeights),
                'min': min(imageHeights),
                'max': max(imageHeights)
            }
        },
        'boundBoxStats': {
            'width': {
                'mean': statistics.mean(boundBoxWidths),
                'median': statistics.median(boundBoxWidths),
                'min': min(boundBoxWidths),
                'max': max(boundBoxWidths),
                'stdev': statistics.stdev(boundBoxWidths) if len(boundBoxWidths) > 1 else 0
            },
            'height': {
                'mean': statistics.mean(boundBoxHeights),
                'median': statistics.median(boundBoxHeights),
                'min': min(boundBoxHeights),
                'max': max(boundBoxHeights),
                'stdev': statistics.stdev(boundBoxHeights) if len(boundBoxHeights) > 1 else 0
            },
            'area': {
                'mean': statistics.mean(boundBoxAreas),
                'median': statistics.median(boundBoxAreas),
                'min': min(boundBoxAreas),
                'max': max(boundBoxAreas)
            }
        },
        'classBoundBoxStats': {},
        'metadata': {
            'truncated': nooftruncatedimages,
            'occluded': noofoccludedimages,
            'difficult': noofdifficultimages
        }
    }
    
    for classname in numberOfClasses.keys():
        results['classBoundBoxStats'][classname] = {
            'width': {
                'mean': statistics.mean(classBoundBoxWidths[classname]),
                'min': min(classBoundBoxWidths[classname]),
                'max': max(classBoundBoxWidths[classname])
            },
            'height': {
                'mean': statistics.mean(classBoundBoxHeights[classname]),
                'min': min(classBoundBoxHeights[classname]),
                'max': max(classBoundBoxHeights[classname])
            }
        }
    
    return results


def printStats(results):
    print(f"total images: {results['totalImages']}")
    print(f"total faces: {results['totalFaces']}")
    print(f"images with multiple faces: {results['imagesWithMultipleFaces']} " f"({results['imagesWithMultipleFaces']/results['totalImages']*100:.1f}%)")
    print(f"\nfaces per image:")
    print(f" mean: {results['facesPerImage']['mean']:.2f}")
    print(f" median: {results['facesPerImage']['median']:.1f}")
    print(f" min: {results['facesPerImage']['min']}")
    print(f" max: {results['facesPerImage']['max']}")
    
    total = results['totalFaces']
    for className, count in sorted(results['noOfClasses'].items()):
        percentage = (count / total) * 100
        print(f"{className:30} {count:5} ({percentage:5.1f}%)")
    
    counts = list(results['noOfClasses'].values())
    maxCount = max(counts)
    minCount = min(counts)
    ratioOfImbalance = maxCount / minCount if minCount > 0 else float('inf')
    
    print(f"\n class imbalance ratio: {ratioOfImbalance:.2f}:1")
    if ratioOfImbalance > 3:
        print(" a lot of class imbalance detected")
    elif ratioOfImbalance > 2:
        print("minor imbalance detected")
    else:
        print("reasonable balance")
    

    print(f"width: mean= {results['imageDimensions']['width']['mean']:.0f}px, "
          f"range=[{results['imageDimensions']['width']['min']}-" f"{results['imageDimensions']['width']['max']}]px")
    print(f"height: mean={results['imageDimensions']['height']['mean']:.0f}px, "
          f"range=[{results['imageDimensions']['height']['min']}-" f"{results['imageDimensions']['height']['max']}]px")
    
    boundingBox = results['boundBoxStats']
    print(f"width: mean={boundingBox['width']['mean']:.1f}px, "
          f"median={boundingBox['width']['median']:.1f}px, " f"range=[{boundingBox['width']['min']}-{boundingBox['width']['max']}]px")
    print(f"height: mean={boundingBox['height']['mean']:.1f}px, "
          f"median={boundingBox['height']['median']:.1f}px, " f"range=[{boundingBox['height']['min']}-{boundingBox['height']['max']}]px")
    print(f"area: mean={boundingBox['area']['mean']:.0f}px², "
          f"median={boundingBox['area']['median']:.0f}px², " f"range=[{boundingBox['area']['min']}-{boundingBox['area']['max']}]px²")
    
    # checking for tiny faces
    smallThreshold = 30
    tinyThreshold = 20
    if boundingBox['width']['min'] < tinyThreshold or boundingBox['height']['min'] < tinyThreshold:
        print(f"\n very small faces detected (< {tinyThreshold}px)")
    elif boundingBox['width']['min'] < smallThreshold or boundingBox['height']['min'] < smallThreshold:
        print(f"\n some small faces detected (< {smallThreshold}px)")
    
    for className in sorted(results['classBoundBoxStats'].keys()):
        stats = results['classBoundBoxStats'][className]
        print(f"\n{className}:")
        print(f" width: mean={stats['width']['mean']:.1f}px, " f"range=[{stats['width']['min']}-{stats['width']['max']}]px")
        print(f" height: mean={stats['height']['mean']:.1f}px, " f"range=[{stats['height']['min']}-{stats['height']['max']}]px")
    

    meta = results['metadata']
    print(f"truncated faces: {meta['truncated']} " f"({meta['truncated']/results['totalFaces']*100:.1f}%)")
    print(f"occluded faces: {meta['occluded']} " f"({meta['occluded']/results['totalFaces']*100:.1f}%)")
    print(f"difficult faces:  {meta['difficult']} " f"({meta['difficult']/results['totalFaces']*100:.1f}%)")


if __name__ == "__main__":
    xmlPath = "C:/Users/Zain Ul Ibad/Desktop/projects/facemaskdetector/annotations"
    print(f"current path: {xmlPath}\n")
    
    if not os.path.exists(xmlPath):
        print(f"directory not found: {xmlPath}")
    else:
        results = analyzeDataset(xmlPath)
        printStats(results)