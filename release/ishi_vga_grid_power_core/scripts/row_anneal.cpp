// Design-owned row assignment search. All dimensions/constraints are inputs.
// No placement, cell geometry, or process rules are embedded in this solver.
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>
using namespace std;

int main(int argc, char **argv) {
    if (argc != 4) return 2;
    ifstream in(argv[1]);
    int nc, nn, nr, cap, restarts, steps, seed, spread_weight;
    double hot, cold;
    in >> nc >> nn >> nr >> cap >> restarts >> steps >> seed >> hot >> cold >> spread_weight;
    vector<int> width(nc), initial(nc);
    for (auto &v : width) in >> v;
    for (auto &v : initial) in >> v;
    vector<vector<int>> nets(nn), incident(nc);
    for (int n=0; n<nn; ++n) {
        int k; in >> k; nets[n].resize(k);
        for (auto &c : nets[n]) { in >> c; incident[c].push_back(n); }
    }
    if (!in || nr > 32) return 3;
    vector<int> global_best = initial;
    int global_score = 1000000000;
    auto save = [&](const vector<int>& state, int energy, int restart) {
        ofstream out(argv[2]);
        out << energy << ' ' << restart << '\n';
        for (int r : state) out << r << ' ';
        out << '\n';
    };
    for (int restart=0; restart<restarts; ++restart) {
        mt19937 rng(seed+restart);
        uniform_real_distribution<double> uni(0.,1.);
        vector<int> state = (restart % 3 == 2) ? global_best : initial;
        vector<int> load(nr,0);
        vector<vector<int>> counts(nn, vector<int>(nr,0));
        for (int c=0;c<nc;++c) load[state[c]] += width[c];
        if (*max_element(load.begin(),load.end()) > cap) { cerr << "initial row exceeds capacity\n"; return 4; }
        for (int n=0;n<nn;++n) for (int c:nets[n]) ++counts[n][state[c]];
        auto cost = [&](int n) {
            int lo=nr, hi=-1, occupied=0;
            for (int r=0;r<nr;++r) if (counts[n][r]) { lo=min(lo,r); hi=r; ++occupied; }
            return occupied ? hi-lo + spread_weight*(occupied-1) : 0;
        };
        int energy=0;
        for (int n=0;n<nn;++n) energy += cost(n);
        if (energy < global_score) { global_score=energy; global_best=state; save(state,energy,restart); }
        vector<int> seen(nn,0), affected;
        int stamp=0;
        for (int step=0;step<steps;++step) {
            int a=rng()%nc, b=(rng()%100 < 78) ? int(rng()%nc) : -1;
            int ra=state[a], rb=b>=0 ? state[b] : rng()%nr;
            if (ra==rb) continue;
            int wa=width[a], wb=b>=0 ? width[b] : 0;
            if (load[ra]-wa+wb > cap || load[rb]+wa-wb > cap) continue;
            affected.clear(); ++stamp;
            for (int n:incident[a]) if (seen[n]!=stamp) { affected.push_back(n); seen[n]=stamp; }
            if (b>=0) for (int n:incident[b]) if (seen[n]!=stamp) { affected.push_back(n); seen[n]=stamp; }
            int delta=0;
            for (int n:affected) delta-=cost(n);
            for (int n:incident[a]) { --counts[n][ra]; ++counts[n][rb]; }
            if (b>=0) for (int n:incident[b]) { --counts[n][rb]; ++counts[n][ra]; }
            for (int n:affected) delta+=cost(n);
            double temp=hot*pow(cold/hot,double(step)/steps);
            if (delta<=0 || uni(rng)<exp(-double(delta)/temp)) {
                state[a]=rb;
                if (b>=0) state[b]=ra;
                load[ra]+=-wa+wb; load[rb]+=wa-wb;
                energy+=delta;
                if (energy<global_score) { global_score=energy; global_best=state; save(state,energy,restart); }
            } else {
                for (int n:incident[a]) { ++counts[n][ra]; --counts[n][rb]; }
                if (b>=0) for (int n:incident[b]) { ++counts[n][rb]; --counts[n][ra]; }
            }
        }
        ofstream per(string(argv[3])+"_"+to_string(restart)+".txt");
        per << energy << '\n'; for (int r:state) per << r << ' '; per << '\n';
        cout << "restart=" << restart << " final=" << energy << " global_best=" << global_score << endl;
    }
}
