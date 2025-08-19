#pragma once

#include <algorithm>
#include <fstream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

#include "nlohmann/json.hpp"

inline double interpolate(double x, const std::vector<double>& xs, const std::vector<double>& ys) {
    if (xs.empty() || ys.empty() || xs.size() != ys.size()) {
        throw std::runtime_error("Invalid interpolation data");
    }
    if (x <= xs.front()) return ys.front();
    if (x >= xs.back()) return ys.back();
    auto upper = std::upper_bound(xs.begin(), xs.end(), x);
    size_t i = std::distance(xs.begin(), upper) - 1;
    double x0 = xs[i], x1 = xs[i + 1];
    double y0 = ys[i], y1 = ys[i + 1];
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0);
}

inline const nlohmann::json& load_calib(const std::string& path = "tech_calib.json") {
    static nlohmann::json calib;
    static bool loaded = false;
    if (!loaded) {
        std::ifstream f(path);
        if (!f) {
            throw std::runtime_error("Unable to open calibration file: " + path);
        }
        f >> calib;
        loaded = true;
    }
    return calib;
}

inline double gate_energy(int node_nm, double vdd, const std::string& gate,
                          const std::string& path = "tech_calib.json") {
    const auto& calib = load_calib(path);

    // Collect available nodes
    std::vector<int> nodes;
    nodes.reserve(calib.size());
    for (auto it = calib.begin(); it != calib.end(); ++it) {
        nodes.push_back(std::stoi(it.key()));
    }
    std::sort(nodes.begin(), nodes.end());

    // For each node, interpolate energy over VDD
    std::vector<double> energies_at_nodes;
    energies_at_nodes.reserve(nodes.size());
    for (int node : nodes) {
        const auto& node_table = calib.at(std::to_string(node));
        std::vector<double> volts;
        std::vector<double> vals;
        volts.reserve(node_table.size());
        vals.reserve(node_table.size());
        for (auto it = node_table.begin(); it != node_table.end(); ++it) {
            double v = std::stod(it.key());
            volts.push_back(v);
            vals.push_back(it.value()["gates"].at(gate).get<double>());
        }
        // sort by voltage
        std::vector<size_t> idx(volts.size());
        std::iota(idx.begin(), idx.end(), 0);
        std::sort(idx.begin(), idx.end(), [&](size_t a, size_t b) { return volts[a] < volts[b]; });
        std::vector<double> v_sorted, val_sorted;
        v_sorted.reserve(idx.size());
        val_sorted.reserve(idx.size());
        for (size_t i : idx) {
            v_sorted.push_back(volts[i]);
            val_sorted.push_back(vals[i]);
        }
        double v_clamped = std::min(std::max(vdd, v_sorted.front()), v_sorted.back());
        energies_at_nodes.push_back(interpolate(v_clamped, v_sorted, val_sorted));
    }

    // Interpolate across nodes
    std::vector<double> node_d(nodes.begin(), nodes.end());
    double n_clamped = std::min(std::max(static_cast<double>(node_nm), node_d.front()), node_d.back());
    return interpolate(n_clamped, node_d, energies_at_nodes);
}

