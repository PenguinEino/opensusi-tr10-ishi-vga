// Animation ECO search: prefer horizontal M1 and vertical M2.
// Fork of the design-owned maze_grid.cpp; fixed old routes use the old solver.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <queue>
#include <vector>
int main(int argc,char**argv){
 if(argc!=3)return 2;
 std::ifstream f(argv[1],std::ios::binary);int32_t h[5];f.read((char*)h,sizeof h);
 int w=h[0],ny=h[1],vc=h[2],maxnodes=h[3],penalty=h[4],n=w*ny;
 std::vector<uint8_t> allow(2*n),via(n),start(2*n),goal(2*n);
 f.read((char*)allow.data(),2*n);f.read((char*)via.data(),n);
 f.read((char*)start.data(),2*n);f.read((char*)goal.data(),2*n);
 if(!f)return 3;
 using Item=std::pair<int,int>;
 std::priority_queue<Item,std::vector<Item>,std::greater<Item>> q;
 std::vector<int> dist(2*n,INT32_MAX),prev(2*n,-1);
 for(int i=0;i<2*n;i++)if(start[i]&&allow[i]){dist[i]=0;q.push({0,i});}
 int end=-1,count=0;
 while(!q.empty()){
  auto [d,i]=q.top();q.pop();if(d!=dist[i])continue;
  if(++count>maxnodes)break;
  if(goal[i]){end=i;break;}
  int z=i/n,j=i%n,x=j%w,y=j/w;
  auto relax=[&](int k,int cost){if(allow[k]&&d+cost<dist[k]){dist[k]=d+cost;prev[k]=i;q.push({dist[k],k});}};
  if(x)relax(i-1,z?penalty:1);if(x+1<w)relax(i+1,z?penalty:1);
  if(y)relax(i-w,z?1:penalty);if(y+1<ny)relax(i+w,z?1:penalty);
  if(via[j])relax((1-z)*n+j,vc);
 }
 std::cerr<<"expanded="<<count<<" found="<<(end>=0)<<"\n";
 if(end<0)return 1;
 std::vector<int> path;for(int i=end;i>=0;i=prev[i])path.push_back(i);
 std::reverse(path.begin(),path.end());std::ofstream out(argv[2]);
 for(int i:path)out<<i/n<<" "<<(i%n)%w<<" "<<(i%n)/w<<"\n";
 std::cerr<<"path_nodes="<<path.size()<<" cost="<<dist[end]<<"\n";
}
