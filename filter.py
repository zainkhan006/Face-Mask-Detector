import os
import json
from collections import defaultdict
import xml.etree.ElementTree as eTree

def parseAndFilter(xmlPath, minFaceSizeinPixel = 25, maxFacesPerImage = 50):
    tree = eTree.parse(xmlPath)
    root = tree.getroot()

    #image info
    filename = root.find('filename').text
    size = root.find('size')
    width = int(size.find('width').text)
    height = int(size.find('height').text)

    #parse all faces
    validFaces = []
    filteredFaces = {
        'smallFace' :0,
        'details' : []
    }

    #gets class label for images
    for object in root.findall('object'):
        className = object.find('name')
        if className is None:
            className = object.find('n')
        classLabel = className.text

        #bounding box details
        boundBox = object.find('bndbox') 
        xMin = int(boundBox.find('xmin').text)
        yMin = int(boundBox.find('ymin').text)
        xMax = int(boundBox.find('xmax').text)
        yMax = int(boundBox.find('ymax').text)

        boundBoxWidth = xMax -xMin
        boundBoxHeight = yMax - yMin

        if boundBoxWidth >= minFaceSizeinPixel and boundBoxHeight >= minFaceSizeinPixel:
            validFaces.append({
                'class' : classLabel,
                'boundBox': (xMin, yMin, xMax, yMax),
                'width': boundBoxWidth,
                'height': boundBoxHeight
            })
        else:
            filteredFaces['smallFace'] += 1
            filteredFaces['details'].append({
                'class': classLabel,
                'width': boundBoxWidth,
                'height': boundBoxHeight
            })

    #skip image with alot of faces(THAT 100+ faces image)
    totalNoOfFaces = len(validFaces) + filteredFaces['smallFace']
    if totalNoOfFaces > maxFacesPerImage:
        return None, 'tooManyFaces'

    #skip images with no valud filtering
    if len(validFaces) == 0:
        return None, 'noValidFaces'

    return{
        'filename': filename,
        'imageWidth': width,
        'imageHeight': height, 
        'faces': validFaces,
        'filteredFaces': filteredFaces
    }, None

def filterDataset(xmlPath, minFaceSizeinPixel = 25, maxFacesPerImage = 50):
    xmlFiles = [f for f in os.listdir(xmlPath) if f.endswith('.xml')] 
    print(f"found {len(xmlFiles)} xml files")

    validImages = []
    skippedImages = {
        'tooManyFaces': [],
        'noValidFaces': []
    }

    preFilterClassCount = defaultdict(int)
    postFilterClassCount = defaultdict(int)
    totalFilteredFaces = 0

    for xmlFile in xmlFiles:
        xmlDirectory = os.path.join(xmlPath, xmlFile)
        try:
            result, skippingReason = parseAndFilter(xmlDirectory, minFaceSizeinPixel=minFaceSizeinPixel, maxFacesPerImage=maxFacesPerImage)
            if result is None:
                skippedImages[skippingReason].append(xmlDirectory)
            else:
                #count faces before filtering
                for face in result['faces']:
                    postFilterClassCount[face['class']] += 1
                for filteredface in result['filteredFaces']['details']:
                    preFilterClassCount[filteredface['class']]+=1
                totalFilteredFaces += result['filteredFaces']['smallFace']
                validImages.append(result)

        except Exception as e:
            print(f"error processing {xmlDirectory} as {e}")
            skippedImages['error'] = skippedImages.get('error', [])
            skippedImages['error'].append(xmlDirectory)
    
    #combine pre and post filtering images
    allClasses = set(list(preFilterClassCount.keys()) + list(postFilterClassCount.keys()))
    for classes in allClasses:
        #prefilterclasscount changing to now have all filtered out faces
        preFilterClassCount[classes] = preFilterClassCount.get(classes, 0) + postFilterClassCount.get(classes, 0)
    
    facesBeforeFiltering = sum(preFilterClassCount.values())
    facesAfterFiltering = sum(postFilterClassCount.values())

    output = {
        'filteringParameters': {
            'minFaceSize': minFaceSizeinPixel,
            'maxFacesPerImage': maxFacesPerImage 
        },
        'stats':{
            'images': {
                'totalOriginalPics': len(xmlFiles),
                'totalValidPics': len(validImages),
                'totalSkippedPics': len(xmlFiles) - len(validImages)
            },
            'faces': {
                'totalFacesBeforeFiltering': facesBeforeFiltering,
                'totalFacesAfterFiltering': facesAfterFiltering,
                'totalFacesFiltered':totalFilteredFaces,
                'facesKept': ((facesAfterFiltering/facesBeforeFiltering)*100) if facesBeforeFiltering > 0 else 0
            },
            'classDistrBeforeFiltering': dict(preFilterClassCount),
            'classDistrAfterFiltering': dict(postFilterClassCount),
            'skippedImages': {
                'tooManyFaces': len(skippedImages.get('tooManyFaces', [])),
                'noValidFaces': len(skippedImages.get('noValidFaces', [])),
                'errors': len(skippedImages.get('error', []))
            }
        },

        'validImages' : validImages,
        'skippedDetails': skippedImages
    }
    return output

def FilterReport(output):
    stats = output['stats']
    parameters = output['filteringParameters']

    print(f"min face size: {parameters['minFaceSize']} * {parameters['minFaceSize']} px")
    print(f"max faces per image: {parameters['maxFacesPerImage']} faces")
    print(f"original images: {stats['images']['totalOriginalPics']} images")
    print(f"valid images: {stats['images']['totalValidPics']} images")
    print(f"ratio: {stats['images']['totalValidPics'] / stats['images']['totalOriginalPics']* 100:.1f}%")
    print(f"skipped images: {stats['images']['totalSkippedPics']}")

    if stats['skippedImages']['tooManyFaces'] > 0:
        print("too many faces")
    if stats['skippedImages']['noValidFaces'] > 0:
        print("no valid faces")
    if stats['skippedImages']['errors'] > 0:
        print("error")

    print(f"total faces before filtering: {stats['faces']['totalFacesBeforeFiltering']} faces")
    print(f"total faces after filtering: {stats['faces']['totalFacesAfterFiltering']} faces")
    print(f"total faces filtered out: {stats['faces']['totalFacesFiltered'] } faces")
    print(f"retained faces rate: {stats['faces']['facesKept']}%")

    allClasses = set(list(stats['classDistrBeforeFiltering'].keys()) + list(stats['classDistrAfterFiltering'].keys()))
    for classes in sorted(allClasses):
        before = stats['classDistrBeforeFiltering'].get(classes, 0)
        after = stats['classDistrAfterFiltering'].get(classes, 0)
        change = after - before
        changepercent = (change / before * 100) if before > 0 else 0
        
        print(f"{classes:<30} {before:<15} {after:<15} {change:+} {changepercent:+.1f}%")
    
    total = stats['faces']['totalFacesAfterFiltering']
    for classes in sorted(stats['classDistrAfterFiltering'].keys()):
        count = stats['classDistrAfterFiltering'][classes]
        percent = (count / total * 100) if total > 0 else 0
        print(f"{classes:<30} {count:5} ({percent:5.1f}%)")
    
    counts = list(stats['classDistrAfterFiltering'].values())
    if len(counts) > 0 and min(counts) > 0:
        imbalanceRatio = max(counts) / min(counts)
        print(f"class imbalance ratio: {imbalanceRatio:.2f}:1")
        if imbalanceRatio > 20:
            print("severe imbalance")
        elif imbalanceRatio > 10:
            print("high imbalance")
        elif imbalanceRatio > 5:
            print("moderate imbalance")
        else:
            print("ok imbalance")

if __name__ == "__main__":
    xmlPath = "C:/Users/Zain Ul Ibad/Desktop/projects/facemaskdetector/annotations"
    result = filterDataset(xmlPath, minFaceSizeinPixel=25, maxFacesPerImage=50)
    FilterReport(result)