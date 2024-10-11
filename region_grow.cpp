#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <queue>
#include <vector>
#include <iostream>
#include <cstdint>

namespace py = pybind11;

void regionGrow(const py::array_t<uint8_t>& seed_image, const py::array_t<float>& grow_image, py::array_t<uint8_t>& output_image, float threshold) {
    auto seeds = seed_image.unchecked<2>();
    auto grow = grow_image.unchecked<2>();
    auto output = output_image.mutable_unchecked<2>();

    int rows = seeds.shape(0);
    int cols = seeds.shape(1);
    
    if(rows != grow_image.shape(0) || cols != grow_image.shape(1) || rows != output_image.shape(0) || cols != output_image.shape(1))
    {
        std::cout<<"The input images do not have the same shape. Clip them before running region growing using imageCM.py\n";
    }   
    
    std::queue<std::pair<int, int>> pixelQueue;
    std::vector<std::vector<bool>> visited(rows, std::vector<bool>(cols, false));
    std::cout<<"Reading seeds\n";
    for (int y = 0; y < rows; ++y) {
        for (int x = 0; x < cols; ++x) {
            if (seeds(y, x) == 1) {
                pixelQueue.push({x, y});
                visited[y][x] = true;
                if(grow(y,x) <= threshold && grow(y,x) > -9999)//only those intersecting with the sar water is recorded
                    output(y, x) = 1;

            }
        }
    }
    std::cout<<"Region growing from "<<pixelQueue.size()<<" seeds using threshold of "<<threshold<<std::endl;
    std::vector<std::pair<int, int>> directions = {{0, 1}, {1, 0}, {0, -1}, {-1, 0}};
    
    while (!pixelQueue.empty()) {
        auto [x, y] = pixelQueue.front();
        pixelQueue.pop();

        for (const auto& dir : directions) {
            int newX = x + dir.first;
            int newY = y + dir.second;

            if (newX >= 0 && newX < cols && newY >= 0 && newY < rows) {
                if(grow(newY, newX) <= -9999) continue;
                if (!visited[newY][newX] && grow(newY, newX) <= threshold) {
                    pixelQueue.push({newX, newY});
                    visited[newY][newX] = true;
                    output(newY, newX) = 1;

                }
            }
        }
    }
    std::cout<<"Region growing is done, returning the image for writing\n";
}

PYBIND11_MODULE(rgrow_flood, m) {
    m.def("rgrow", &regionGrow, "Region grow algorithm",
          py::arg("seed_image"), py::arg("grow_image"), py::arg("output_image"), py::arg("threshold"));
}
