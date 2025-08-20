#pragma once

#include <algorithm>
#include <fstream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
#include <map>
#include <regex>

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

using GateMap = std::map<std::string, double>;
using VddMap = std::map<double, GateMap>;
using CalibData = std::map<int, VddMap>;

inline const CalibData& load_calib(const std::string& path = "tech_calib.json") {
    static CalibData calib;
    static bool loaded = false;
    if (!loaded) {
        std::ifstream f(path);
        if (!f) {
            throw std::runtime_error("Unable to open calibration file: " + path);
        }
        std::string line;
        int current_node = 0;
        double current_vdd = 0.0;
        bool in_node = false;
        bool in_vdd = false;
        while (std::getline(f, line)) {
            std::string t;
            for (char c : line) {
                if (!std::isspace(static_cast<unsigned char>(c))) {
                    t += c;
                }
            }
            if (t.empty()) {
                continue;
            }
            if (t.back() == ',') {
                t.pop_back();
            }
            if (t.rfind("\"gates\":{", 0) == 0 && in_node && in_vdd) {
                std::string gates = t.substr(std::string("\"gates\":{").size());
                if (!gates.empty() && gates.back() == '}') {
                    gates.pop_back();
                }
                std::regex gate_re("\"([^\"]+)\":([0-9eE+.-]+)");
                auto it = std::sregex_iterator(gates.begin(), gates.end(), gate_re);
                auto end = std::sregex_iterator();
                for (; it != end; ++it) {
                    const std::string gate = (*it)[1];
                    double val = std::stod((*it)[2]);
                    calib[current_node][current_vdd][gate] = val;
                }
            } else if (t.front() == '"' && t.find("\":{") != std::string::npos) {
                std::string key = t.substr(1, t.find('"', 1) - 1);
                if (!in_node) {
                    current_node = std::stoi(key);
                    in_node = true;
                } else {
                    current_vdd = std::stod(key);
                    in_vdd = true;
                }
            } else if (t == "}") {
                if (in_vdd) {
                    in_vdd = false;
                } else if (in_node) {
                    in_node = false;
                }
            }
        }
        loaded = true;
    }
    return calib;
}

inline double gate_energy(int node_nm, double vdd, const std::string& gate,
                          const std::string& path = "tech_calib.json") {
    const auto& calib = load_calib(path);

    std::vector<int> nodes;
    nodes.reserve(calib.size());
    for (const auto& kv : calib) {
        nodes.push_back(kv.first);
    }
    std::sort(nodes.begin(), nodes.end());

    std::vector<double> energies_at_nodes;
    energies_at_nodes.reserve(nodes.size());
    for (int node : nodes) {
        const auto& node_table = calib.at(node);
        std::vector<double> volts;
        std::vector<double> vals;
        volts.reserve(node_table.size());
        vals.reserve(node_table.size());
        for (const auto& vpair : node_table) {
            volts.push_back(vpair.first);
            vals.push_back(vpair.second.at(gate));
        }
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

    std::vector<double> node_d(nodes.begin(), nodes.end());
    double n_clamped = std::min(std::max(static_cast<double>(node_nm), node_d.front()), node_d.back());
    return interpolate(n_clamped, node_d, energies_at_nodes);
}

