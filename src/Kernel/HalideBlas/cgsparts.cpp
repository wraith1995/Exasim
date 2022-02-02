#include <stdio.h>
#include "Halide.h"
using namespace Halide;


class MTGenerator : public Generator<MTGenerator> {
public:
  Input<Buffer<double, 2>> A{"A"};
  Input<Buffer<double, 1>> x{"H"};
  Output<Buffer<double>> result{"result", 1}; //A^Tx -- we don't need to worry about copying over here.w


  GeneratorParam<int> dofs_{"dofs", 1000000};
  GeneratorParam<bool> usedofs {"usedofs", true};
  GeneratorParam<int> maxortho{"maxortho", 32};
  GeneratorParam<bool> vectorize_{"vectorize", true};
  GeneratorParam<int> block_size_ = {"block_size", 1 << 8};

  Var i = Var("i");
  Var j = Var("j");
  void generate (){
    //    Func result("result");


    const Expr dofs = usedofs ? dofs_ : A.width();
    const Expr sum_size = dofs;
    const Expr size = A.height();
    const int vec_size = vectorize_ ? natural_vector_size(type_of<double>()) : 1;
    const Expr sum_size_vecs = sum_size / vec_size;
    const int unroll_size = std::min(vec_size, 4);
    

    Func prod("prod");
    prod(j, i) = A(j, i) * x(j);
    RDom k(0, sum_size_vecs, "k");
    Func accum_vecs("accum_vecs");
    accum_vecs(j, i) += prod(k * vec_size + j, i);

    Func accum_vecs_transpose("accum_vecs_transpose");
    accum_vecs_transpose(i, j) = accum_vecs(j, i);

    RDom lanes(0, vec_size);
    Func sum_lanes("sum_lanes");
    sum_lanes(i) += accum_vecs_transpose(i, lanes);

    RDom tail(sum_size_vecs * vec_size, sum_size - sum_size_vecs * vec_size);
    Func sum_tail("sum_tail");
    sum_tail(i) = sum_lanes(i);
    sum_tail(i) += prod(tail, i);

    Func ATx("ATx");
    ATx(i) = sum_tail(i);
    result(i) = ATx(i);


    Var ii("ii"), t("t");
    result.specialize((sum_size / vec_size) * vec_size == sum_size)
      .specialize(size >= unroll_size)
      .vectorize(i, unroll_size)
      .specialize(size >= block_size_)
      .split(i, t, i, block_size_ / unroll_size)
      .parallel(t);

    result
      .specialize(size >= unroll_size)
      .vectorize(i, unroll_size)
      .specialize(size >= block_size_)
      .split(i, t, i, block_size_ / unroll_size)
      .parallel(t);

    accum_vecs
      .compute_at(result, i)
      .unroll(i)
      .unroll(j)
      .update()
      .reorder(i, j, k)
      .unroll(i)
      .unroll(j);
    accum_vecs_transpose
      .compute_at(result, i)
      .unroll(i)
      .unroll(j);
    sum_lanes
      .compute_at(result, i)
      .update()
      .unroll(lanes);
    sum_tail
      .compute_at(result, i)
      .update()
      .reorder(i, tail);

    if (vectorize_) {
      accum_vecs.vectorize(j)
	.update()
	.vectorize(j);
      accum_vecs_transpose.vectorize(j);

      sum_lanes.specialize(size >= vec_size).vectorize(i, vec_size);
      sum_lanes.update().specialize(size >= vec_size).vectorize(i, vec_size);

      sum_tail.specialize(size >= vec_size).vectorize(i, vec_size);
      sum_tail.update().specialize(size >= vec_size).vectorize(i, vec_size);
    }

    A.dim(0).set_min(0).dim(1).set_min(0);
    x.dim(0).set_bounds(0, dofs);
  };

  
};

class MGenerator : public Generator<MGenerator> {
public:
  Input<Buffer<double, 2>> A{"A"};
  Input<Buffer<double, 1>> ATx{"ATx"};
  Input<Buffer<double, 1>> x{"x"};
  Output<Buffer<double, 1>> output{"result"}; //normalize((I-AA^T)x)
  Output<double> norm{"norm"};

  GeneratorParam<int> dofs_{"dofs", 1000000};
  GeneratorParam<bool> usedofs {"usedofs", true};
  GeneratorParam<int> maxortho{"maxortho", 32};
  GeneratorParam<bool> vectorize_{"vectorize", true};
  GeneratorParam<int> block_size_ = {"block_size", 1 << 8};

  Var i = Var("i");
  Var j = Var("j");
  void generate (){
    Func result("result");


    const int vec_size = vectorize_ ? natural_vector_size(type_of<double>()) : 1;
    const int unroll_size = std::min(vec_size, 4);
    const Expr dofs = usedofs ? dofs_ : x.width();
    const Expr size = dofs;
    const Expr sum_size = A.height();
    const Expr sum_size_cols = (sum_size / unroll_size) * unroll_size;
    const Expr tail_size = sum_size - sum_size_cols;

    RDom k(0, sum_size_cols, "k");
    RDom tail(sum_size_cols, tail_size, "tail");
    Func block("block");
    block(i) = x(i);
    block(i) -= A(i, k) * ATx(k);
    block(i) -= A(i, tail) * ATx(tail);
    result(i) = block(i);



    

    RVar ki("ki");
    Var ii("ii");
    result.specialize(tail_size == 0)
      .specialize(size >= vec_size)
      .vectorize(i, vec_size)
      .specialize(size >= unroll_size * vec_size)
      .unroll(i, unroll_size)
      .specialize(size >= block_size_)
      .split(i, i, ii, block_size_ / (unroll_size * vec_size))
      .parallel(i);

    result.specialize(size >= vec_size)
      .vectorize(i, vec_size)
      .specialize(size >= unroll_size * vec_size)
      .unroll(i, unroll_size)
      .specialize(size >= block_size_)
      .split(i, i, ii, block_size_ / (unroll_size * vec_size))
      .parallel(i);

    block.compute_at(result, i);
    block.specialize(size >= vec_size)
      .vectorize(i, vec_size);
    block.update()
      .specialize(size >= vec_size && sum_size >= unroll_size)
      .split(i, i, ii, vec_size)
      .split(k, k, ki, unroll_size)
      .reorder(ii, ki, i, k)
      .vectorize(ii)
      .unroll(ki);
    block.update()
      .specialize(size >= vec_size)
      .vectorize(i, vec_size);
    block.update(1)
      .reorder(i, tail)
      .specialize(size >= vec_size)
      .vectorize(i, vec_size)
      .specialize(sum_size >= unroll_size)
      .unroll(i, unroll_size);

    A.dim(0).set_min(0).dim(1).set_min(0);
    ATx.dim(0).set_bounds(0, A.height());
    x.dim(0).set_bounds(0, dofs);


    
    Expr size_vecs = size / vec_size;
    Expr size_tail = size - size_vecs * vec_size;
    Func normp("normp");
    if (vectorize_) {
      Func dot("dot");
      RDom k(0, size_vecs);
      dot(i) += result(k * vec_size + i) * result(k * vec_size + i);

      RDom lanes(0, vec_size);
      RDom tail(size_vecs * vec_size, size_tail);
      normp() = sum(dot(lanes));
      normp() += sum(result(tail) * result(tail));

      dot.compute_root().vectorize(i);
      dot.update(0).vectorize(i);
    } else {
      RDom k(0, size);
      normp() = sum(result(k) * result(k));
    }
    normp.compute_root();
    norm() = sqrt(normp());
    

    output(i) = result(i)/norm();
    result.compute_root();



    const Expr sizep = dofs;
    Var iii("iii");
    output.specialize(sizep >= vec_size)
      .vectorize(i, vec_size)
      .specialize(sizep >= unroll_size * vec_size)
      .unroll(i, unroll_size)
      .specialize(sizep >= block_size_)
      .split(i, i, iii, block_size_ / (unroll_size * vec_size))
      .parallel(i);


  };
};

HALIDE_REGISTER_GENERATOR(MTGenerator, dgemtv)
HALIDE_REGISTER_GENERATOR(MGenerator, dgemvnormed)

